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

        $amountStr = $request->input('amount') ?? '';
        $rawText = $request->input('raw_text') ?? '';
        
        // Bersihkan string dari ,00 atau .00 di akhir
        $cleanStr = preg_replace('/[,.]00$/', '', $amountStr);
        $amount = preg_replace('/[^0-9]/', '', $cleanStr);
        
        // Fallback jika amount kosong, cari angka di raw_text
        if (!$amount && $rawText) {
            // Cari pola seperti Rp 5.023 atau 5,023
            if (preg_match('/(?:Rp|IDR)?\s*([0-9]{1,3}(?:[.,][0-9]{3})+)(?:[,.]00)?/', $rawText, $matches)) {
                $amount = preg_replace('/[^0-9]/', '', preg_replace('/[,.]00$/', '', $matches[1]));
            }
        }

        $sourceApp = $request->input('source_app');
        $reference = $request->input('reference');

        if (!$amount) {
            return response()->json(['status' => 'error', 'message' => 'Amount not found in payload'], 400);
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

            // Check double_saldo voucher
            $meta = $transaction->metadata;
            if (isset($meta['applied_voucher']) && $meta['applied_voucher']['type'] === 'double_saldo') {
                $vCode = $meta['applied_voucher']['code'];
                $benefitValue = floatval($meta['applied_voucher']['benefit_value'] ?? 0);

                $voucher = \App\Models\Voucher::where('code', $vCode)->first();
                if ($voucher && $voucher->is_active && $voucher->used_count < $voucher->usage_limit) {
                    $bonus = $transaction->amount;
                    if ($benefitValue > 0 && $bonus > $benefitValue) {
                        $bonus = $benefitValue;
                    }

                    if ($bonus > 0) {
                        $user->balance += $bonus;
                        $user->save();

                        \App\Models\VoucherUsage::create([
                            'user_id' => $user->id,
                            'voucher_id' => $voucher->id,
                            'benefit_type' => 'double_saldo',
                            'benefit_amount' => $bonus,
                        ]);

                        $voucher->increment('used_count');

                        Transaction::create([
                            'reference' => 'VCH-' . strtoupper(\Illuminate\Support\Str::random(10)),
                            'user_id' => $user->id,
                            'type' => 'topup',
                            'amount' => $bonus,
                            'unique_code' => 0,
                            'total_amount' => $bonus,
                            'status' => 'success',
                            'description' => "Bonus Double Saldo Voucher ({$voucher->code})",
                        ]);

                        Notification::create([
                            'user_id' => $user->id,
                            'type' => 'order',
                            'message' => "Selamat! Anda mendapatkan bonus Double Saldo sebesar Rp " . number_format($bonus, 0, ',', '.') . " dari voucher {$voucher->code}.",
                        ]);
                    }
                }
            }
            
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
            $userStr = $meta['username'] ?? ($meta['tg_id'] ?? 'user');
            $exp = $meta['days'] ?? 30;
            $pw = $meta['password'] ?? '1';
            $ip = $meta['ip_limit'] ?? ($meta['limit_ip'] ?? '1');
            $sni = $meta['sni_config'] ?? '3';
            $quota = $meta['quota'] ?? '0';

            // Jika transaksi dari Telegram Bot, biarkan Bot yang mengeksekusi agar bisa kirim text ke user
            if (isset($meta['source']) && $meta['source'] === 'telegram_bot') {
                \App\Models\Notification::create([
                    'user_id' => $user->id,
                    'type' => 'order',
                    'message' => "Pembayaran berhasil. Layanan VPN $protocol Anda sedang diproses oleh Bot Telegram.",
                ]);
                return response()->json(['status' => 'success', 'message' => 'Delegated to Telegram Bot'], 200);
            }

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

        // Send Telegram Notification if transaction was initiated from Bot Telegram
        try {
            $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
            $tgId = $meta['tg_id'] ?? null;
            if ($tgId) {
                $msg = "";
                if ($transaction->type === 'topup') {
                    $msg = "✅ **Top Up Saldo Berhasil!**\n\n"
                         . "💰 Nominal: `Rp " . number_format($transaction->amount, 0, ',', '.') . "`\n"
                         . "🔢 Kode Unik: `Rp " . $transaction->unique_code . "`\n"
                         . "💵 Total Masuk: `Rp " . number_format($transaction->total_amount, 0, ',', '.') . "`\n\n"
                         . "Saldo Anda telah otomatis ditambahkan.";
                } else {
                    $msg = "✅ **Pembayaran Berhasil!**\n\n"
                         . "Layanan Anda telah otomatis diproses.";
                }
                $this->sendTelegramNotification($tgId, $msg);
            }
        } catch (\Exception $e) {
            \Illuminate\Support\Facades\Log::error("Telegram Bot notification failed: " . $e->getMessage());
        }

        return response()->json(['status' => 'success']);
    }

    public function status($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->firstOrFail();

        if ($transaction->status === 'pending') {
            $isExpired = $transaction->created_at->addMinutes(5)->isPast();
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

    protected function sendTelegramNotification($tgId, $message)
    {
        // Fetch BOT_TOKEN
        $varPath = '/usr/bin/kyt/var.txt';
        $botToken = null;
        if (file_exists($varPath)) {
            $content = file_get_contents($varPath);
            if (preg_match("/BOT_TOKEN='(.*?)'/m", $content, $matches)) {
                $botToken = $matches[1];
            }
        }
        
        if (!$botToken) {
            // Fallback to setting/env
            $botToken = env('TELEGRAM_BOT_TOKEN');
        }
        
        if ($botToken && $tgId) {
            $url = "https://api.telegram.org/bot{$botToken}/sendMessage";
            $data = [
                'chat_id' => $tgId,
                'text' => $message,
                'parse_mode' => 'Markdown',
            ];
            
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_TIMEOUT, 5);
            curl_exec($ch);
            curl_close($ch);
        }
    }
}
