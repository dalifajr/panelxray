<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Setting;
use App\Models\Transaction;
use App\Models\Notification;
use App\Models\User;
use Illuminate\Support\Facades\Log;

class PaymentController extends Controller
{
    public function processListener(Request $request)
    {
        $secretKey = Setting::where('key', 'payment_secret_key')->value('value');

        // Pengecekan Header Wajib
        $timestamp = $request->header('X-Timestamp');
        $signature = $request->header('X-Signature');
        $idempotencyKey = $request->header('X-Idempotency-Key');

        if (!$timestamp || !$signature || !$idempotencyKey) {
            return response()->json(['status' => 'error', 'message' => 'Missing required headers'], 400);
        }

        if ($request->header('Content-Type') !== 'application/json') {
            return response()->json(['status' => 'error', 'message' => 'Invalid Content-Type'], 400);
        }

        if (!$secretKey) {
            return response()->json(['status' => 'error', 'message' => 'Secret key is not configured in system'], 500);
        }

        // Validasi HMAC Signature
        $body = $request->getContent();
        $expectedSignature = hash_hmac('sha256', $timestamp . '.' . $body, $secretKey);

        if (!hash_equals($expectedSignature, $signature)) {
            Log::warning("Payment Listener: Invalid signature from " . $request->ip());
            return response()->json(['status' => 'error', 'message' => 'Unauthorized: Invalid signature'], 401);
        }

        $amountStr = $request->input('amount');
        // Bersihkan amount misal "Rp 5.023" -> 5023
        $amount = preg_replace('/[^0-9]/', '', $amountStr);
        $sourceApp = $request->input('source_app');
        $reference = $request->input('reference');
        $rawText = $request->input('raw_text');

        if (!$amount) {
            return response()->json(['status' => 'error', 'message' => 'Amount not found'], 400);
        }

        // Pengecekan Idempotency (cegah proses ganda untuk event yang sama)
        // Kita bisa menyimpan Idempotency-Key di kolom metadata transaksi, 
        // atau kita pastikan transaksi yang 'pending' saja yang diproses.
        
        // Cari transaksi pending dengan total_amount cocok
        $transaction = Transaction::where('status', 'pending')
            ->where('total_amount', $amount)
            ->first();

        if (!$transaction) {
            Log::warning("Payment Listener: No pending transaction found for amount $amount from app $sourceApp");
            return response()->json(['status' => 'error', 'message' => 'Transaction not found'], 404);
        }

        // Update metadata dengan info pembayaran
        $meta = $transaction->metadata ?? [];
        $meta['payment_info'] = [
            'idempotency_key' => $idempotencyKey,
            'source_app' => $sourceApp,
            'reference' => $reference,
            'raw_text' => $rawText,
            'timestamp' => $timestamp
        ];
        $transaction->metadata = $meta;

        // Jika ketemu, sukseskan
        $transaction->status = 'success';
        $transaction->save();

        $user = User::find($transaction->user_id);

        if ($transaction->type === 'topup') {
            // Tambah saldo
            $user->balance += $transaction->total_amount;
            $user->save();

            Notification::create([
                'user_id' => $user->id,
                'type' => 'order',
                'message' => "Top Up Saldo senilai Rp " . number_format($transaction->total_amount, 0, ',', '.') . " berhasil diproses dan masuk ke dompet Anda.",
            ]);
            
            // Notify Admin
            $admins = User::where('role', 'admin')->get();
            foreach ($admins as $admin) {
                Notification::create([
                    'user_id' => $admin->id,
                    'type' => 'order',
                    'message' => "User {$user->username} berhasil Top Up saldo Rp " . number_format($transaction->total_amount, 0, ',', '.'),
                ]);
            }
        } elseif ($transaction->type === 'vpn_purchase') {
            // Ini untuk pembayaran pesanan langsung (Direct Order)
            // Saldo tidak ditambah, tapi pesanan VPN dijalankan.
            // Implementasinya diproses via job/command atau langsung memanggil fungsi pembuatan.
            // Karena fungsi buat vpn ada di controller VPN, kita akan ubah status jadi success
            // dan user saat merefresh halaman akan melihat akunnya siap,
            // atau kita panggil service buat VPN di sini.
            
            // Note: Pada tahap berikutnya, kita harus menghubungkan ini dengan pembuatan akun.
            $vpnService = app(\App\Services\VpnService::class);
            $meta = $transaction->metadata;
            // Contoh: $meta = ['protocol' => 'vmess', 'username' => 'test', 'days' => 30, 'limit_ip' => 2];
            try {
                // Di sini memanggil fungsi buat. Kita serahkan pada VpnController nanti.
                Notification::create([
                    'user_id' => $user->id,
                    'type' => 'order',
                    'message' => "Pembayaran pesanan VPN {$meta['protocol']} ({$meta['username']}) Rp " . number_format($transaction->total_amount, 0, ',', '.') . " berhasil diterima.",
                ]);
                
                // Notify Admin
                $admins = User::where('role', 'admin')->get();
                foreach ($admins as $admin) {
                    Notification::create([
                        'user_id' => $admin->id,
                        'type' => 'order',
                        'message' => "Pesanan baru dibayar! VPN {$meta['protocol']} oleh {$user->username}.",
                    ]);
                }
            } catch (\Exception $e) {
                Log::error("Failed to create VPN after payment: " . $e->getMessage());
                // Kembalikan ke saldo jika gagal?
            }
        }

        return response()->json(['status' => 'success', 'message' => 'Payment processed']);
    }
}
