<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Transaction;
use App\Models\User;
use App\Models\Notification;
use App\Models\VpnAccount;
use App\Services\VpnService;
use Illuminate\Support\Facades\Log;

class OrderController extends Controller
{
    public function index(Request $request)
    {
        $status = $request->get('status', 'all');
        $search = $request->get('search', '');
        
        $query = Transaction::with('user')->orderBy('created_at', 'desc');
        
        if ($status !== 'all') {
            $query->where('status', $status);
        }
        
        if (!empty($search)) {
            $query->where(function($q) use ($search) {
                $q->where('reference', 'LIKE', "%{$search}%")
                  ->orWhere('description', 'LIKE', "%{$search}%")
                  ->orWhereHas('user', function($uq) use ($search) {
                      $uq->where('username', 'LIKE', "%{$search}%");
                  });
            });
        }
        
        $orders = $query->paginate(15);
        
        return view('admin.orders', compact('orders', 'status', 'search'));
    }
    
    public function approve($id)
    {
        $transaction = Transaction::findOrFail($id);
        
        if ($transaction->status !== 'pending') {
            return back()->with('sweet_error', 'Hanya pesanan pending yang dapat disetujui.');
        }
        
        $user = User::find($transaction->user_id);
        
        try {
            if ($transaction->type === 'topup') {
                $user->balance += $transaction->total_amount;
                $user->save();
                
                Notification::create([
                    'user_id' => $user->id,
                    'type' => 'order',
                    'message' => "Top Up Saldo senilai Rp " . number_format($transaction->total_amount, 0, ',', '.') . " telah disetujui oleh Admin.",
                ]);
            } elseif ($transaction->type === 'vpn_purchase_qris') {
                $vpnService = app(VpnService::class);
                $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
                $protocol = $meta['protocol'] ?? 'vmess';
                $userStr = $meta['username'] ?? 'user';
                $exp = $meta['days'] ?? 30;
                $pw = $meta['password'] ?? '1';
                $ip = $meta['limit_ip'] ?? '1';
                $sni = $meta['sni_config'] ?? '3';
                $quota = $meta['quota'] ?? '0';
                
                $isExist = false;
                if ($protocol !== 'ssh') {
                    $resCheck = $vpnService->executeBash("grep -w \"$userStr\" /etc/xray/config.json | wc -l");
                    if (intval(trim($resCheck['output'])) > 0) $isExist = true;
                } else {
                    $resCheck = $vpnService->executeBash("id -u $userStr >/dev/null 2>&1 && echo 1 || echo 0");
                    if (intval(trim($resCheck['output'])) === 1) $isExist = true;
                }

                if ($isExist) {
                    throw new \Exception("Username '$userStr' sudah terpakai.");
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
                    $vpnService->registerAccountToDb('', $protocol, $userStr, $exp, false);
                    VpnAccount::create([
                        'user_id' => $user->id,
                        'vpn_username' => $userStr,
                        'service' => $protocol
                    ]);

                    Notification::create([
                        'user_id' => $user->id,
                        'type' => 'order',
                        'message' => "Pembayaran pesanan VPN {$protocol} ({$userStr}) telah dilunasi oleh Admin. Akun Anda telah aktif.",
                    ]);
                } else {
                    throw new \Exception("Gagal eksekusi pembuatan VPN di sistem.");
                }
            } elseif ($transaction->type === 'vpn_renew_qris') {
                $vpnService = app(VpnService::class);
                $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
                $protocol = $meta['protocol'] ?? 'vmess';
                $userStr = $meta['username'] ?? 'user';
                $days = (int) ($meta['days'] ?? 30);
                $quota = (int) ($meta['quota'] ?? 0);
                $limit_ip = (int) ($meta['limit_ip'] ?? 1);

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

                    Notification::create([
                        'user_id' => $user->id,
                        'type' => 'order',
                        'message' => "Perpanjangan VPN {$protocol} ({$userStr}) telah dilunasi oleh Admin. Masa aktif bertambah {$days} hari.",
                    ]);
                } else {
                    throw new \Exception("Gagal eksekusi perpanjangan VPN di sistem.");
                }
            }
            
            $transaction->status = 'success';
            $transaction->save();
            
            return back()->with('sweet_success', 'Pesanan berhasil disetujui dan diproses.');
            
        } catch (\Exception $e) {
            Log::error("Manual approve error: " . $e->getMessage());
            return back()->with('sweet_error', 'Gagal memproses pesanan: ' . $e->getMessage());
        }
    }
    
    public function cancel(Request $request, $id)
    {
        $transaction = Transaction::findOrFail($id);
        
        if ($transaction->status !== 'pending') {
            return back()->with('sweet_error', 'Hanya pesanan pending yang dapat dibatalkan.');
        }
        
        $reason = $request->input('reason', '-');
        if (empty(trim($reason))) {
            $reason = '-';
        }
        
        $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
        $meta = $meta ?: [];
        $meta['cancel_reason'] = $reason;
        
        $transaction->status = 'cancelled';
        $transaction->metadata = $meta;
        $transaction->save();
        
        Notification::create([
            'user_id' => $transaction->user_id,
            'type' => 'order',
            'message' => "Pesanan Anda ({$transaction->reference}) dibatalkan oleh Admin. Alasan: {$reason}",
        ]);
        
        return back()->with('sweet_success', 'Pesanan berhasil dibatalkan.');
    }
}
