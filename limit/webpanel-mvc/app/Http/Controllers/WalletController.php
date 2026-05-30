<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\Transaction;
use App\Models\User;
use App\Models\Setting;
use Illuminate\Support\Str;
use App\Helpers\QrisHelper;
use Carbon\Carbon;

class WalletController extends Controller
{
    public function index()
    {
        $transactions = Auth::user()->transactions()->orderBy('created_at', 'desc')->paginate(10);
        
        // Find pending topup
        $pendingTopup = Auth::user()->transactions()->where('status', 'pending')->where('type', 'topup')->first();
        
        if ($pendingTopup) {
            // Check if 5 minutes expired
            if (Carbon::now()->diffInSeconds($pendingTopup->created_at) >= 300) {
                $pendingTopup->update(['status' => 'cancelled']);
                return redirect()->route('wallet.index')->with('sweet_error', 'Waktu pembayaran topup telah habis. Dibatalkan.');
            }
        }

        $qrisPayload = Setting::where('key', 'qris_payload')->value('value');
        
        $dynamicQris = null;
        if ($qrisPayload && $pendingTopup) {
            $dynamicQris = QrisHelper::generateDynamic($qrisPayload, $pendingTopup->total_amount);
        }
        
        return view('customer.wallet', compact('transactions', 'pendingTopup', 'qrisPayload', 'dynamicQris'));
    }

    public function topup(Request $request)
    {
        $request->validate([
            'amount' => 'required|integer|min:5000',
            'voucher_code' => 'nullable|string|max:30',
        ]);

        $amount = $request->amount;
        
        // Cek kelipatan 5000
        if ($amount % 5000 !== 0) {
            return back()->with('sweet_error', 'Nominal top up harus kelipatan Rp 5.000');
        }

        $voucher = null;
        if ($request->filled('voucher_code')) {
            $code = strtoupper(trim($request->voucher_code));
            $voucher = \App\Models\Voucher::where('code', $code)->first();

            if (!$voucher) {
                return back()->with('sweet_error', 'Kode voucher tidak ditemukan!');
            }

            // Check if active
            if (!$voucher->is_active) {
                return back()->with('sweet_error', 'Voucher ini sudah tidak aktif!');
            }

            // Check usage limit
            if ($voucher->used_count >= $voucher->usage_limit) {
                return back()->with('sweet_error', 'Kuota penggunaan voucher ini sudah habis!');
            }

            // Check expiration
            if ($voucher->expires_at && $voucher->expires_at->isPast()) {
                return back()->with('sweet_error', 'Voucher ini sudah kedaluwarsa!');
            }

            // Check if user already claimed this voucher
            $alreadyUsed = \App\Models\VoucherUsage::where('user_id', Auth::id())
                ->where('voucher_id', $voucher->id)
                ->exists();
            if ($alreadyUsed) {
                return back()->with('sweet_error', 'Anda sudah pernah menggunakan voucher ini!');
            }
        }

        // Cancel existing pending topups to avoid confusion
        Auth::user()->transactions()->where('status', 'pending')->where('type', 'topup')->update(['status' => 'cancelled']);

        $uniqueCode = rand(1, 100);
        $totalAmount = $amount + $uniqueCode;

        $metadata = [];
        $description = 'Top Up Saldo via QRIS';

        if ($voucher) {
            if ($voucher->type === 'free_balance') {
                // For free_balance, redeem it immediately!
                $this->free_balance($voucher, Auth::user());
                // After redeeming free_balance, proceed with creating topup normally.
                $metadata['applied_voucher'] = [
                    'code' => $voucher->code,
                    'type' => 'free_balance',
                    'benefit_value' => $voucher->benefit_value
                ];
            } elseif ($voucher->type === 'double_saldo') {
                // For double_saldo, store in metadata to double it when the payment is completed!
                $metadata['applied_voucher'] = [
                    'code' => $voucher->code,
                    'type' => 'double_saldo',
                    'benefit_value' => $voucher->benefit_value
                ];
                $description = 'Top Up Saldo via QRIS + Bonus Double Saldo';
            }
        }

        Transaction::create([
            'reference' => 'TOP-' . strtoupper(Str::random(10)),
            'user_id' => Auth::id(),
            'type' => 'topup',
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'status' => 'pending',
            'description' => $description,
            'metadata' => !empty($metadata) ? $metadata : null,
        ]);

        if ($voucher && $voucher->type === 'free_balance') {
            return back()->with('sweet_success', 'Voucher Saldo Gratis berhasil diklaim (Saldo masuk Rp ' . number_format($voucher->benefit_value, 0, ',', '.') . ')! Silakan lanjutkan pembayaran instruksi top up Anda.');
        }

        return back()->with('sweet_success', 'Instruksi top up berhasil dibuat. Silakan lakukan pembayaran!');
    }

    public function redeemVoucher(Request $request)
    {
        $request->validate([
            'voucher_code' => 'required|string|max:30',
        ]);

        $code = strtoupper(trim($request->voucher_code));
        $voucher = \App\Models\Voucher::where('code', $code)->first();

        if (!$voucher) {
            return back()->with('sweet_error', 'Kode voucher tidak ditemukan!');
        }

        // Check if active
        if (!$voucher->is_active) {
            return back()->with('sweet_error', 'Voucher ini sudah tidak aktif!');
        }

        // Check usage limit
        if ($voucher->used_count >= $voucher->usage_limit) {
            return back()->with('sweet_error', 'Kuota penggunaan voucher ini sudah habis!');
        }

        // Check expiration
        if ($voucher->expires_at && $voucher->expires_at->isPast()) {
            return back()->with('sweet_error', 'Voucher ini sudah kedaluwarsa!');
        }

        // Check if user already claimed this voucher
        $alreadyUsed = \App\Models\VoucherUsage::where('user_id', Auth::id())
            ->where('voucher_id', $voucher->id)
            ->exists();
        if ($alreadyUsed) {
            return back()->with('sweet_error', 'Anda sudah pernah menggunakan voucher ini!');
        }

        // Execute specific method matching the voucher type!
        $type = $voucher->type;
        if (method_exists($this, $type)) {
            return $this->$type($voucher, Auth::user());
        }

        return back()->with('sweet_error', 'Tipe benefit voucher tidak valid.');
    }

    protected function free_balance($voucher, $user)
    {
        // 1. Add balance to user
        $user->balance += $voucher->benefit_value;
        $user->save();

        // 2. Log voucher usage
        \App\Models\VoucherUsage::create([
            'user_id' => $user->id,
            'voucher_id' => $voucher->id,
            'benefit_type' => 'free_balance',
            'benefit_amount' => $voucher->benefit_value,
        ]);

        // 3. Increment voucher used count
        $voucher->increment('used_count');

        // 4. Create successful transaction log
        Transaction::create([
            'reference' => 'VCH-' . strtoupper(Str::random(10)),
            'user_id' => $user->id,
            'type' => 'topup',
            'amount' => $voucher->benefit_value,
            'unique_code' => 0,
            'total_amount' => $voucher->benefit_value,
            'status' => 'success',
            'description' => "Klaim Voucher Saldo Gratis ({$voucher->code})",
        ]);

        // 5. Send notification
        \App\Models\Notification::create([
            'user_id' => $user->id,
            'type' => 'system',
            'message' => 'Selamat! Anda berhasil mengklaim voucher ' . $voucher->code . ' dan mendapatkan saldo gratis sebesar Rp ' . number_format($voucher->benefit_value, 0, ',', '.') . '.',
        ]);

        return back()->with('sweet_success', 'Selamat! Voucher berhasil diklaim. Saldo Anda bertambah Rp ' . number_format($voucher->benefit_value, 0, ',', '.') . '!');
    }

    protected function double_saldo($voucher, $user)
    {
        return back()->with('sweet_error', 'Voucher jenis Double Saldo harus dimasukkan pada kolom voucher saat melakukan Top Up agar nominal deposit Anda berlipat ganda.');
    }

    public function cancelTopup()
    {
        $pending = Auth::user()->transactions()->where('status', 'pending')->where('type', 'topup')->first();
        if ($pending) {
            $pending->update(['status' => 'cancelled']);
            return back()->with('sweet_success', 'Transaksi top up berhasil dibatalkan.');
        }
        return back()->with('sweet_error', 'Tidak ada transaksi yang dapat dibatalkan.');
    }

    public function adminFinance(Request $request)
    {
        $filter = $request->get('filter', 'all'); // harian, mingguan, bulanan, all
        
        $query = Transaction::where('status', 'success')->where('type', 'vpn_purchase');
        
        if ($filter == 'harian') {
            $query->whereDate('created_at', today());
        } elseif ($filter == 'mingguan') {
            $query->whereBetween('created_at', [now()->startOfWeek(), now()->endOfWeek()]);
        } elseif ($filter == 'bulanan') {
            $query->whereMonth('created_at', now()->month)->whereYear('created_at', now()->year);
        }
        
        $totalPendapatan = $query->sum('total_amount');
        
        // Pelanggan royal (paling banyak transaksi vpn purchase)
        $royalCustomers = User::whereHas('transactions', function($q) {
            $q->where('status', 'success')->where('type', 'vpn_purchase');
        })
        ->withSum(['transactions' => function($q) {
            $q->where('status', 'success')->where('type', 'vpn_purchase');
        }], 'total_amount')
        ->orderBy('transactions_sum_total_amount', 'desc')
        ->take(10)
        ->get();

        $recentTransactions = Transaction::with('user')->orderBy('created_at', 'desc')->paginate(15);

        return view('admin.finance', compact('totalPendapatan', 'royalCustomers', 'recentTransactions', 'filter'));
    }
}
