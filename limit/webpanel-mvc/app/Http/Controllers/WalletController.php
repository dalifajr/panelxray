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
            if (Carbon::now()->diffInMinutes($pendingTopup->created_at) >= 5) {
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
        ]);

        $amount = $request->amount;
        
        // Cek kelipatan 5000
        if ($amount % 5000 !== 0) {
            return back()->with('sweet_error', 'Nominal top up harus kelipatan Rp 5.000');
        }

        // Cancel existing pending topups to avoid confusion
        Auth::user()->transactions()->where('status', 'pending')->where('type', 'topup')->update(['status' => 'cancelled']);

        $uniqueCode = rand(1, 100);
        $totalAmount = $amount + $uniqueCode;

        Transaction::create([
            'reference' => 'TOP-' . strtoupper(Str::random(10)),
            'user_id' => Auth::id(),
            'type' => 'topup',
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'status' => 'pending',
            'description' => 'Top Up Saldo via QRIS',
        ]);

        return back()->with('sweet_success', 'Instruksi top up berhasil dibuat. Silakan lakukan pembayaran!');
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
