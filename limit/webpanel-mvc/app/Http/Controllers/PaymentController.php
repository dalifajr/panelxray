<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Setting;
use App\Models\Transaction;
use App\Models\Notification;
use App\Models\User;
use Illuminate\Support\Facades\Log;
use Carbon\Carbon;

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

        if (!$secretKey) {
            return response()->json(['status' => 'error', 'message' => 'Secret key is not configured on server'], 500);
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
            Log::info("Payment Listener: No pending transaction found for amount $amount from app $sourceApp (Ignored)");
            return response()->json(['status' => 'ignored', 'message' => 'Transaction not found, but payload received'], 200);
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
        } elseif ($transaction->type === 'vpn_purchase_qris') {
            $vpnService = app(\App\Services\VpnService::class);
            $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
            $protocol = $meta['protocol'] ?? 'vmess';
            $userStr = $meta['username'] ?? 'user';
            $exp = $meta['days'] ?? 30;
            $pw = $meta['password'] ?? '1';
            $ip = $meta['limit_ip'] ?? '1';
            $sni = $meta['sni_config'] ?? '3';
            $quota = $meta['quota'] ?? '0';

            try {
                // Pengecekan apakah username sudah terpakai
                $isExist = false;
                if ($protocol !== 'ssh') {
                    $resCheck = $vpnService->executeBash("grep -w \"$userStr\" /etc/xray/config.json | wc -l");
                    if (intval(trim($resCheck['output'])) > 0) $isExist = true;
                } else {
                    $resCheck = $vpnService->executeBash("id -u $userStr >/dev/null 2>&1 && echo 1 || echo 0");
                    if (intval(trim($resCheck['output'])) === 1) $isExist = true;
                }

                if ($isExist) {
                    throw new \Exception("Username '$userStr' sudah terpakai oleh user lain.");
                }

                $res = null;
                if ($protocol === 'ssh') {
                    $later = date('Y-m-d', strtotime("+$exp days"));
                    $res = $vpnService->executeBash("useradd -e $later -s /bin/false -M $userStr && echo \"$userStr:$pw\" | chpasswd");
                    if ($res['success']) {
                        $vpnService->executeBash("mkdir -p /etc/kyt/limit/ssh/ip && echo \"$ip\" > /etc/kyt/limit/ssh/ip/$userStr");
                    }
                } else {
                    $scriptMap = [
                        'vmess' => 'addws',
                        'vless' => 'addvless',
                        'trojan' => 'addtr',
                        'shadowsocks' => 'addss'
                    ];
                    $cmd = $scriptMap[$protocol] ?? 'addws';
                    $inputLines = [$sni, $userStr, $exp, $quota, $ip];
                    $res = $vpnService->executeBashWithStdin($cmd, implode("\n", $inputLines) . "\n");
                }

                if ($res && $res['success']) {
                    // Update ke sqlite db kyt
                    $vpnService->registerAccountToDb('', $protocol, $userStr, $exp, false);
                    
                    // Update Laravel DB
                    \App\Models\VpnAccount::create([
                        'user_id' => $user->id,
                        'vpn_username' => $userStr,
                        'service' => $protocol
                    ]);

                    \App\Models\Notification::create([
                        'user_id' => $user->id,
                        'type' => 'order',
                        'message' => "Pembayaran pesanan VPN {$protocol} ({$userStr}) berhasil. Akun Anda telah aktif.",
                    ]);
                    
                    // Notify Admin
                    $admins = \App\Models\User::where('role', 'admin')->get();
                    foreach ($admins as $admin) {
                        \App\Models\Notification::create([
                            'user_id' => $admin->id,
                            'type' => 'order',
                            'message' => "Pesanan baru dibayar! VPN {$protocol} oleh {$user->username}.",
                        ]);
                    }
                } else {
                    throw new \Exception("Gagal eksekusi pembuatan VPN di sistem.");
                }
            } catch (\Exception $e) {
                \Illuminate\Support\Facades\Log::error("Failed to create VPN after payment: " . $e->getMessage());
                // Refund ke saldo
                $user->balance += $transaction->total_amount;
                $user->save();
                
                \App\Models\Notification::create([
                    'user_id' => $user->id,
                    'type' => 'order',
                    'message' => "Gagal membuat VPN {$protocol} ({$userStr}). Alasan: " . $e->getMessage() . ". Dana sebesar Rp " . number_format($transaction->total_amount, 0, ',', '.') . " telah dikembalikan ke Saldo Akun Anda. Silakan buat ulang menggunakan Saldo.",
                ]);
            }
        } elseif ($transaction->type === 'vpn_renew_qris') {
            $vpnService = app(\App\Services\VpnService::class);
            $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
            $protocol = $meta['protocol'] ?? 'vmess';
            $userStr = $meta['username'] ?? 'user';
            $days = (int) ($meta['days'] ?? 30);
            $quota = (int) ($meta['quota'] ?? 0);
            $limit_ip = (int) ($meta['limit_ip'] ?? 1);

            try {
                if ($protocol === 'ssh') {
                    $res = $vpnService->renewSshAccount($userStr, $days, $limit_ip);
                } else {
                    $res = $vpnService->renewXrayAccount($protocol, $userStr, $days, $quota, $limit_ip);
                }

                if ($res && !empty($res['success'])) {
                    $newExpiry = $res['expires_at'] ?? null;
                    if ($newExpiry) {
                        $vpnService->updateAccountExpiry($protocol, $userStr, $newExpiry);
                    }

                    // Reactivate/Unsuspend and convert to normal account if it was a trial
                    $acc = \App\Models\VpnAccount::where('service', $protocol)->where('vpn_username', $userStr)->first();
                    if ($acc && $acc->is_trial) {
                        if ($protocol === 'ssh') {
                            $vpnService->executeBash("usermod -U $userStr");
                        } else {
                            $scriptMap = ['vmess' => 'unsuspws', 'vless' => 'unsuspvless', 'trojan' => 'unsusptr', 'shadowsocks' => 'unsuspss'];
                            $cmd = $scriptMap[$protocol] ?? 'unsuspws';
                            $vpnService->executeBash("$cmd --user $userStr");
                        }
                        
                        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=1, is_trial=0 WHERE service='{$protocol}' AND username='{$userStr}'\"); c.commit()";
                        $vpnService->executeBashWithStdin("python3 -", $dbScript);

                        $acc->is_trial = false;
                        $acc->admin_suspended = false;
                        $acc->save();
                    }
                    
                    \App\Models\Notification::create([
                        'user_id' => $user->id,
                        'type' => 'order',
                        'message' => "Perpanjangan VPN {$protocol} ({$userStr}) berhasil. Masa aktif bertambah {$days} hari.",
                    ]);
                } else {
                    throw new \Exception("Gagal eksekusi perpanjangan VPN di sistem.");
                }
            } catch (\Exception $e) {
                \Illuminate\Support\Facades\Log::error("Failed to renew VPN after payment: " . $e->getMessage());
                // Refund ke saldo
                $user->balance += $transaction->total_amount;
                $user->save();
                
                \App\Models\Notification::create([
                    'user_id' => $user->id,
                    'type' => 'order',
                    'message' => "Gagal memperpanjang VPN {$protocol} ({$userStr}). Alasan: " . $e->getMessage() . ". Dana sebesar Rp " . number_format($transaction->total_amount, 0, ',', '.') . " telah dikembalikan ke Saldo Akun Anda.",
                ]);
            }
        }

        return response()->json(['status' => 'success']);
    }

    public function status($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->firstOrFail();

        if ($transaction->status === 'pending') {
            $isExpired = Carbon::now()->diffInSeconds($transaction->created_at) >= 300;
            if ($isExpired && in_array($transaction->type, ['topup', 'vpn_purchase_qris', 'vpn_renew_qris'], true)) {
                $meta = $transaction->metadata;
                if (!is_array($meta)) {
                    $meta = [];
                }
                if (in_array($transaction->type, ['vpn_purchase_qris', 'vpn_renew_qris'], true)) {
                    $meta['cancel_reason'] = $meta['cancel_reason'] ?? 'Waktu pembayaran habis.';
                }
                $transaction->metadata = $meta;
                $transaction->status = 'cancelled';
                $transaction->save();
            }
        }

        return response()->json(['status' => $transaction->status]);
    }

    public function testConnection(Request $request)
    {
        $secretKey = Setting::where('key', 'payment_secret_key')->value('value');

        $timestamp = $request->header('X-Timestamp');
        $signature = $request->header('X-Signature');

        if (!$timestamp || !$signature) {
            return response()->json(['status' => 'error', 'message' => 'Missing required headers'], 400);
        }

        if (!$secretKey) {
            return response()->json(['status' => 'error', 'message' => 'Secret key is not configured in system'], 500);
        }

        $body = $request->getContent();
        $expectedSignature = hash_hmac('sha256', $timestamp . '.' . $body, $secretKey);

        if (!hash_equals($expectedSignature, $signature)) {
            return response()->json(['status' => 'error', 'message' => 'Unauthorized: Invalid signature'], 401);
        }

        return response()->json(['status' => 'success', 'message' => 'Connection OK']);
    }
}
