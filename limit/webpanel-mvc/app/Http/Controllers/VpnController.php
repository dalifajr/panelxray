<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\VpnService;
use Illuminate\Support\Facades\Log;

class VpnController extends Controller
{
    protected $vpn;
    protected $protocols = ['ssh', 'vmess', 'vless', 'trojan', 'shadowsocks'];

    public function __construct(VpnService $vpn)
    {
        $this->vpn = $vpn;
    }

    public function index($protocol)
    {
        if (!in_array($protocol, $this->protocols)) {
            abort(404);
        }

        $parsedUsers = $this->vpn->getAccounts($protocol);
        
        $authUser = auth()->user();
        if ($authUser->role === 'customer') {
            $ownedVpnUsernames = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->pluck('vpn_username')
                ->map(fn($name) => strtolower($name))
                ->toArray();
                
            $parsedUsers = array_filter($parsedUsers, function($user) use ($ownedVpnUsernames) {
                return in_array(strtolower($user['username']), $ownedVpnUsernames);
            });
        } else {
            // Admin: get all owners for mapping
            $vpnAccounts = \App\Models\VpnAccount::with('user')->where('service', $protocol)->get()->keyBy(function($item) {
                return strtolower($item->vpn_username);
            });
            
            foreach ($parsedUsers as &$user) {
                $lowerUser = strtolower($user['username']);
                if (isset($vpnAccounts[$lowerUser]) && $vpnAccounts[$lowerUser]->user) {
                    $u = $vpnAccounts[$lowerUser]->user;
                    $user['creator_name'] = $u->username ?? $u->name;
                } else {
                    $user['creator_name'] = 'Sistem';
                }
            }
        }
        
        $basePrice = \App\Models\Price::where('protocol', $protocol)->value('price') ?? 0;
        
        // Tambahkan akun yang berstatus pending pembayaran (QRIS)
        $pendingQuery = \App\Models\Transaction::whereIn('type', ['vpn_purchase_qris', 'vpn_renew_qris'])
            ->where('status', 'pending');
            
        if ($authUser->role === 'customer') {
            $pendingQuery->where('user_id', $authUser->id);
        }
        
        $pendingTxs = $pendingQuery->get();
        foreach ($pendingTxs as $tx) {
            try {
                $meta = is_string($tx->metadata) ? json_decode($tx->metadata, true) : $tx->metadata;
                if (isset($meta['protocol']) && $meta['protocol'] === $protocol) {
                    // Check if expired
                    if (\Carbon\Carbon::now()->diffInMinutes($tx->created_at) >= 5) {
                        $tx->update(['status' => 'cancelled']);
                        continue;
                    }
                    
                    $parsedUsers[] = [
                        'username' => $meta['username'] ?? 'unknown',
                        'created_at' => $tx->created_at->format('Y-m-d'),
                        'expires_at' => \Carbon\Carbon::now()->addDays($meta['days'] ?? 0)->format('Y-m-d'),
                        'ip_limit' => $meta['limit_ip'] ?? 1,
                        'quota' => $meta['quota'] ?? 0,
                        'status' => 'Menunggu Pembayaran',
                        'is_pending_payment' => true,
                        'active' => 0,
                        'transaction_id' => $tx->id,
                        'creator_name' => $authUser->role === 'admin' ? ($tx->user?->username ?? $tx->user?->name ?? 'Unknown') : 'Anda'
                    ];
                }
            } catch (\Throwable $e) {
                \Illuminate\Support\Facades\Log::error('Error processing pending transaction: ' . $e->getMessage());
            }
        }
        
        return view('vpn.list', compact('protocol', 'parsedUsers', 'basePrice'));
    }

    public function master()
    {
        $parsedUsers = $this->vpn->getAccounts(null); // Fetch all
        return view('vpn.master', compact('parsedUsers'));
    }

    public function viewConfig($protocol, $username)
    {
        if (!in_array($protocol, $this->protocols)) {
            return response()->json(['error' => 'Invalid protocol'], 400);
        }
        $configText = $this->vpn->getAccountConfig($protocol, $username);
        return response()->json(['config' => $configText]);
    }

    public function create($protocol)
    {
        if (!in_array($protocol, $this->protocols)) {
            abort(404);
        }

        $basePrice = \App\Models\Price::where('protocol', $protocol)->value('price') ?? 0;
        
        return view('vpn.create', compact('protocol', 'basePrice'));
    }

    /**
     * Helper: Execute a Python script on the VPS via base64 piping.
     * Delegates to VpnService::runPython for a flat, non-nested execution.
     */
    private function runPython($script)
    {
        return $this->vpn->runPython($script);
    }

    /**
     * Helper: Pipe input lines into a shell command on the VPS.
     * Uses the bridge's native stdin support — no base64 nesting needed.
     */
    private function pipeInputToCommand($lines, $command)
    {
        $stdinData = implode("\n", $lines) . "\n";
        return $this->vpn->executeBashWithStdin($command, $stdinData);
    }

    public function store(Request $request, $protocol)
    {
        if (!in_array($protocol, $this->protocols)) {
            abort(404);
        }

        $validated = $request->validate([
            'username' => 'required|string|max:30|regex:/^[a-zA-Z0-9_.-]+$/',
            'password' => 'nullable|string|max:30',
            'limit_ip' => 'nullable|integer|min:1',
            'expired' => 'required|integer|min:1|max:365',
            'sni_config' => 'nullable|string|in:1,2,3',
            'quota' => 'nullable|integer|min:0',
            'payment_method' => 'nullable|string|in:saldo,qris,trial'
        ]);

        $userStr = $validated['username'];
        $exp = $validated['expired'];
        $pw = $validated['password'] ?? '1';
        $ip = $validated['limit_ip'] ?? '1';
        $sni = $validated['sni_config'] ?? '3';
        $quota = $validated['quota'] ?? '0';
        $paymentMethod = $validated['payment_method'] ?? 'saldo';
        
        $isTrial = $paymentMethod === 'trial';
        if ($isTrial) {
            $exp = 1; // Untuk backend Xray/SSH, kita paksa 1 hari karena tidak mendukung menit.
        }

        $authUser = auth()->user();

        // Harga dan Validasi Saldo (Khusus Customer)
        $totalPrice = 0;
        if ($authUser->role === 'customer') {
            $activeCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->count();
            if ($activeCount >= $authUser->vpn_account_limit) {
                return back()->with('sweet_error', "Gagal membuat akun: Anda telah mencapai batas maksimal pembuatan akun VPN ({$authUser->vpn_account_limit} akun aktif).")->withInput();
            }
            
            // Hitung harga
            $basePriceObj = \App\Models\Price::where('protocol', $protocol)->first();
            $basePrice = $basePriceObj->price ?? 0; // Default 0 jika belum diset
            $ipPriceObj = \App\Models\Price::where('protocol', 'add_ip')->first();
            $ipPrice = $ipPriceObj->price ?? 0;
            
            $vpnCost = round(($basePrice / 30) * $exp);
            $extraIpCost = $ip > 1 ? ($ipPrice * ($ip - 1)) : 0; // Misal harga extra IP flat per pembuatan
            
            $totalPrice = $vpnCost + $extraIpCost;

            // Jika trial, lewati pengecekan harga dan cek limit trial
            if ($isTrial) {
                $totalPrice = 0;
                $trialCount = \App\Models\VpnAccount::where('user_id', $authUser->id)
                    ->where('is_trial', true)
                    ->where('created_at', '>=', now()->subDays(7))
                    ->count();
                if ($trialCount >= 3) {
                    return back()->with('sweet_error', "Batas pembuatan akun Trial tercapai (3 kali per minggu).")->withInput();
                }
            } else {
                if ($totalPrice <= 0) {
                    return back()->with('sweet_error', "Gagal membuat akun: Layanan ini belum memiliki harga. Silakan hubungi Admin.")->withInput();
                }

                if ($paymentMethod === 'saldo' && $authUser->balance < $totalPrice) {
                    return back()->with('sweet_error', "Saldo tidak mencukupi. Total tagihan Rp " . number_format($totalPrice, 0, ',', '.') . ", sedangkan saldo Anda Rp " . number_format($authUser->balance, 0, ',', '.'))->withInput();
                }
            }
        }

        // Pre-flight check: ensure username doesn't already exist
        if ($protocol !== 'ssh') {
            $resCheck = $this->vpn->executeBash("grep -w \"$userStr\" /etc/xray/config.json | wc -l");
            if (intval(trim($resCheck['output'])) > 0) {
                return back()->with('sweet_error', "Gagal membuat akun: Username '$userStr' sudah terdaftar di konfigurasi Xray!")->withInput();
            }
        } else {
            $resCheck = $this->vpn->executeBash("id -u $userStr >/dev/null 2>&1 && echo 1 || echo 0");
            if (intval(trim($resCheck['output'])) === 1) {
                return back()->with('sweet_error', "Gagal membuat akun: Username '$userStr' sudah terdaftar di sistem SSH!")->withInput();
            }
        }

        if ($authUser->role === 'customer' && $paymentMethod === 'qris' && $totalPrice > 0) {
            $uniqueCode = rand(1, 100);
            $finalTotal = $totalPrice + $uniqueCode;
            
            $trx = \App\Models\Transaction::create([
                'reference' => 'VPN-' . strtoupper(\Illuminate\Support\Str::random(10)),
                'user_id' => $authUser->id,
                'type' => 'vpn_purchase_qris',
                'amount' => $totalPrice,
                'unique_code' => $uniqueCode,
                'total_amount' => $finalTotal,
                'status' => 'pending',
                'description' => "Pembelian VPN $protocol ($userStr) $exp Hari",
                'metadata' => [
                    'protocol' => $protocol,
                    'username' => $userStr,
                    'password' => $pw,
                    'days' => $exp,
                    'limit_ip' => $ip,
                    'sni_config' => $sni,
                    'quota' => $quota
                ]
            ]);

            return redirect()->route('checkout.show', $trx->id)->with('sweet_success', 'Pesanan dibuat. Silakan selesaikan pembayaran.');
        }

        $res = null;

        if ($protocol === 'ssh') {
            // SSH creation (useradd)
            $later = date('Y-m-d', strtotime("+$exp days"));
            $res = $this->vpn->executeBash("useradd -e $later -s /bin/false -M $userStr && echo \"$userStr:$pw\" | chpasswd");
            if ($res['success']) {
                $this->vpn->executeBash("mkdir -p /etc/kyt/limit/ssh/ip && echo \"$ip\" > /etc/kyt/limit/ssh/ip/$userStr");
            }
        } else {
            // Xray protocols: pipe input lines to the appropriate add script
            $scriptMap = [
                'vmess' => 'addws',
                'vless' => 'addvless',
                'trojan' => 'addtr',
                'shadowsocks' => 'addss'
            ];
            $cmd = $scriptMap[$protocol] ?? 'addws';

            // Input lines matching the non-interactive read order in the scripts:
            // 1. CFG_CHOICE (SNI config: 1/2/3)
            // 2. username
            // 3. masaaktif (expiry days)
            // 4. Quota (GB)
            // 5. iplimit
            $inputLines = [$sni, $userStr, $exp, $quota, $ip];

            Log::info("CREATE: Piping to $cmd with inputs: " . json_encode($inputLines));
            $res = $this->pipeInputToCommand($inputLines, $cmd);
            Log::info("CREATE result: code={$res['success']}, output=" . substr($res['output'], 0, 500));
        }

        if ($res && $res['success']) {
            if ($paymentMethod === 'saldo' && $totalPrice > 0 && !$isTrial) {
                $authUser->balance -= $totalPrice;
                $authUser->save();

                \App\Models\Transaction::create([
                    'reference' => 'VPN-' . strtoupper(\Illuminate\Support\Str::random(10)),
                    'user_id' => $authUser->id,
                    'type' => 'vpn_purchase',
                    'amount' => $totalPrice,
                    'total_amount' => $totalPrice,
                    'status' => 'success',
                    'description' => "Pembuatan VPN $protocol ($userStr) $exp Hari"
                ]);

                \App\Models\Notification::create([
                    'user_id' => $authUser->id,
                    'type' => 'order',
                    'message' => "Pembelian VPN $protocol ($userStr) berhasil. Saldo terpotong Rp " . number_format($totalPrice, 0, ',', '.'),
                ]);
            }

            // Register to SQLite database
            $tgId = auth()->user()->telegram_id ?? '0';
            $this->vpn->registerAccountToDb($tgId, $protocol, $userStr, $exp, false);
            
            // Catat kepemilikan di database Laravel
            \App\Models\VpnAccount::create([
                'user_id' => auth()->id(),
                'vpn_username' => $userStr,
                'service' => $protocol,
                'is_trial' => $isTrial
            ]);

            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $userStr berhasil dibuat!" . ($isTrial ? ' (Trial 15 Menit)' : ''));
        }

        $debugError = $res['error'] ?? 'Unknown error';
        $debugOutput = $res['output'] ?? '';
        $fullMsg = 'Gagal membuat akun: ' . $debugError;
        if (!empty($debugOutput)) {
            $fullMsg .= "\nOutput Log:\n" . $debugOutput;
        }

        return back()->with('sweet_error', $fullMsg)->withInput();
    }

    public function renewForm($protocol, $user)
    {
        $quota = 0;
        $limit_ip = 1;

        if ($protocol !== 'ssh') {
            // Fetch Quota
            $resQ = $this->vpn->executeBash("cat /etc/{$protocol}/{$user} 2>/dev/null");
            $qBytes = intval(trim($resQ['output']));
            if ($qBytes > 0) {
                $quota = floor($qBytes / (1024 * 1024 * 1024)); // Convert back to GB
            }

            // Fetch IP Limit
            $resIp = $this->vpn->executeBash("cat /etc/kyt/limit/{$protocol}/ip/{$user} 2>/dev/null");
            $lIp = intval(trim($resIp['output']));
            if ($lIp > 0) {
                $limit_ip = $lIp;
            }
        }

        $basePrice = \App\Models\Price::where('protocol', $protocol)->value('price') ?? 0;

        return view('vpn.renew', compact('protocol', 'user', 'quota', 'limit_ip', 'basePrice'));
    }

    public function renew(Request $request, $protocol, $user)
    {
        $authUser = auth()->user();
        
        $validated = $request->validate([
            'days' => 'required|integer|min:1|max:365',
            'quota' => 'nullable|integer|min:0',
            'limit_ip' => 'nullable|integer|min:1',
            'payment_method' => 'nullable|string|in:saldo,qris'
        ]);
        
        $days = $validated['days'];
        $quota = $validated['quota'] ?? 0;
        $limit_ip = $validated['limit_ip'] ?? 1;
        $paymentMethod = $validated['payment_method'] ?? 'saldo';

        $totalPrice = 0;

        if ($authUser->role === 'customer') {
            $owns = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->where('vpn_username', $user)
                ->exists();
            if (!$owns) abort(403, 'Unauthorized action.');

            // Hitung harga perpanjangan (hanya durasi)
            $basePrice = \App\Models\Price::where('protocol', $protocol)->value('price') ?? 0;
            $totalPrice = round(($basePrice / 30) * $days);

            if ($totalPrice <= 0) {
                return back()->with('sweet_error', "Gagal perpanjang: Layanan ini belum memiliki harga. Silakan hubungi Admin.")->withInput();
            }

            if ($paymentMethod === 'saldo' && $authUser->balance < $totalPrice) {
                return back()->with('sweet_error', "Saldo tidak mencukupi untuk perpanjangan. Tagihan: Rp " . number_format($totalPrice, 0, ',', '.'))->withInput();
            }
        }

        if ($authUser->role === 'customer' && $paymentMethod === 'qris' && $totalPrice > 0) {
            $uniqueCode = rand(1, 100);
            $finalTotal = $totalPrice + $uniqueCode;
            
            $trx = \App\Models\Transaction::create([
                'reference' => 'VPNR-' . strtoupper(\Illuminate\Support\Str::random(10)),
                'user_id' => $authUser->id,
                'type' => 'vpn_renew_qris',
                'amount' => $totalPrice,
                'unique_code' => $uniqueCode,
                'total_amount' => $finalTotal,
                'status' => 'pending',
                'description' => "Perpanjangan VPN $protocol ($user) $days Hari",
                'metadata' => [
                    'protocol' => $protocol,
                    'username' => $user,
                    'days' => $days,
                    'limit_ip' => $limit_ip,
                    'quota' => $quota
                ]
            ]);

            return redirect()->route('checkout.show', $trx->id)->with('sweet_success', 'Pesanan perpanjangan dibuat. Silakan selesaikan pembayaran.');
        }

        if ($protocol === 'ssh') {
            $later = date('Y-m-d', strtotime("+$days days"));
            $res = $this->vpn->executeBash("usermod -e $later $user && passwd -u $user");
            $res['success'] = $res['rc'] == 0;
        } else {
            $xrayMarkers = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
            $marker = $xrayMarkers[$protocol] ?? '###';
            $later = date('Y-m-d', strtotime("+$days days"));
            
            $script = <<<PYTHON
import os
path = '/etc/xray/config.json'
marker = '$marker'
username = '$user'
new_expiry = '$later'
protocol = '$protocol'
quota = '$quota'
limit_ip = '$limit_ip'

# If suspended, unsuspend first by calling the script
if os.path.exists(f"/etc/kyt/suspended/{protocol}/{username}"):
    script_map = {'vmess': 'unsuspws', 'vless': 'unsuspvless', 'trojan': 'unsusptr', 'shadowsocks': 'unsuspss'}
    cmd = script_map.get(protocol, 'unsuspws')
    os.system(f"{cmd} --user {username} >/dev/null 2>&1")

try:
    with open(path, 'r') as f:
        lines = f.readlines()
    changed = False
    next_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == marker and parts[1].lower() == username.lower():
            next_lines.append(f"{marker} {username} {new_expiry}\\n")
            changed = True
        else:
            next_lines.append(line)
    
    if not changed:
        print("ERROR: User not found in config.json")
    else:
        with open(path, 'w') as f:
            f.writelines(next_lines)
            
        # Update limits
        os.system(f"mkdir -p /etc/kyt/limit/{protocol}/ip")
        os.system(f"echo {limit_ip} > /etc/kyt/limit/{protocol}/ip/{username}")
        
        os.system(f"mkdir -p /etc/{protocol}")
        if str(quota) != "0":
            q_bytes = int(quota) * 1024 * 1024 * 1024
            os.system(f"echo {q_bytes} > /etc/{protocol}/{username}")
        else:
            os.system(f"rm -f /etc/{protocol}/{username}")
            
        # Update .db file
        os.system(f"awk -v user='{username}' -v exp='{new_expiry}' '{{ if ($1 == \\"{marker}\\" && $2 == user) {{ $3 = exp }} print }}' /etc/{protocol}/.{protocol}.db > /etc/{protocol}/.{protocol}.db.tmp && mv /etc/{protocol}/.{protocol}.db.tmp /etc/{protocol}/.{protocol}.db")
        
        # Restart
        os.system('systemctl restart xray >/dev/null 2>&1')
        print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
PYTHON;
            $res = $this->runPython($script);
            $res['success'] = strpos($res['output'], 'SUCCESS') !== false;
        }

        if (!empty($res['success'])) {
            // Update SQLite DB
            $later = date('Y-m-d', strtotime("+$days days"));
            $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET expires_at='{$later}' WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
            $this->runPython($dbScript);

            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $user berhasil diperpanjang.");
        }

        return back()->with('sweet_error', 'Gagal perpanjang: ' . $res['error'] . "\n" . $res['output']);
    }

    public function suspend($protocol, $user)
    {
        $authUser = auth()->user();
        if ($authUser->role === 'customer') {
            $owns = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->where('vpn_username', $user)
                ->exists();
            if (!$owns) abort(403, 'Unauthorized action.');
        }

        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -L $user");
        } else {
            $scriptMap = [
                'vmess' => 'suspws',
                'vless' => 'suspvless',
                'trojan' => 'susptr',
                'shadowsocks' => 'suspss'
            ];
            $cmd = $scriptMap[$protocol] ?? 'suspws';
            $res = $this->vpn->executeBash("$cmd --user $user --reason manual");
        }

        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET updated_at=date('now') WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $this->runPython($dbScript);

        $acc = \App\Models\VpnAccount::where('service', $protocol)->where('vpn_username', $user)->first();
        if ($acc) {
            $acc->admin_suspended = ($authUser->role === 'admin');
            $acc->save();
        }

        return back()->with('sweet_success', "Akun $user disuspend.");
    }

    public function unsuspend($protocol, $user)
    {
        $authUser = auth()->user();
        if ($authUser->role === 'customer') {
            $owns = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->where('vpn_username', $user)
                ->first();
            if (!$owns) abort(403, 'Unauthorized action.');
            if ($owns->admin_suspended) {
                return back()->with('sweet_error', 'Akun ini disuspend oleh Admin. Anda tidak dapat mengaktifkannya sendiri.');
            }
        }

        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -U $user");
        } else {
            $scriptMap = [
                'vmess' => 'unsuspws',
                'vless' => 'unsuspvless',
                'trojan' => 'unsusptr',
                'shadowsocks' => 'unsuspss'
            ];
            $cmd = $scriptMap[$protocol] ?? 'unsuspws';
            $res = $this->vpn->executeBash("$cmd --user $user");
        }

        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=1 WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $this->runPython($dbScript);

        $acc = \App\Models\VpnAccount::where('service', $protocol)->where('vpn_username', $user)->first();
        if ($acc) {
            $acc->admin_suspended = false;
            $acc->save();
        }

        return back()->with('sweet_success', "Akun $user diaktifkan kembali.");
    }

    public function delete($protocol, $user)
    {
        $authUser = auth()->user();
        if ($authUser->role === 'customer') {
            $owns = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->where('vpn_username', $user)
                ->exists();
            if (!$owns) abort(403, 'Unauthorized action.');
        }

        if ($protocol === 'ssh') {
            $this->vpn->executeBash("userdel -f $user 2>/dev/null; rm -f /etc/kyt/limit/ssh/ip/$user");
        } else {
            $xrayMarkers = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
            $marker = $xrayMarkers[$protocol] ?? '###';
            
            $script = <<<PYTHON
import os, re
path = '/etc/xray/config.json'
marker = '$marker'
username = '$user'
protocol = '$protocol'

try:
    with open(path, 'r') as f:
        lines = f.readlines()
    changed = False
    next_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            # Skip the JSON client line that follows the marker comment
            if '},{"' in line or '},{\"' in line or '"password"' in line or '"id"' in line or '"method"' in line:
                changed = True
                skip_next = False
                continue
            skip_next = False
        stripped = line.strip()
        parts = stripped.split()
        if len(parts) >= 2 and parts[0] == marker and parts[1].lower() == username.lower():
            changed = True
            skip_next = True
            continue
        next_lines.append(line)
    if changed:
        with open(path, 'w') as f:
            f.writelines(next_lines)
        os.system('systemctl restart xray >/dev/null 2>&1')
        
    # Clean up cache, limit, and suspended files regardless of whether it was in config.json
    srv = protocol
    os.system(f"rm -f /etc/kyt/suspended/{srv}/{username}")
    os.system(f"rm -rf /etc/kyt/limit/{srv}/ip/{username}")
    os.system(f"rm -rf /etc/{srv}/{username}")
    os.system(f"sed -i '/\\b{username}\\b/d' /etc/{srv}/.{srv}.db 2>/dev/null")
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
PYTHON;
            $res = $this->runPython($script);
            Log::info("DELETE $protocol/$user result: " . $res['output']);
        }

        // Always clean from SQLite DB regardless
        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"DELETE FROM account_registry WHERE service='{$protocol}' AND username='{$user}'\"); c.commit(); print('DB_OK')";
        $dbRes = $this->runPython($dbScript);
        Log::info("DELETE DB result: " . $dbRes['output']);
        
        // Remove from local vpn_accounts tracking and process refund if applicable
        $acc = \App\Models\VpnAccount::where('vpn_username', $user)->where('service', $protocol)->first();
        if ($acc) {
            $isRefunded = false;
            if (!$acc->is_trial && $acc->created_at && $acc->created_at->diffInMinutes(now()) <= 15) {
                // Find related purchase transaction
                $tx = \App\Models\Transaction::where('user_id', $acc->user_id)
                    ->whereIn('type', ['vpn_purchase', 'vpn_purchase_qris'])
                    ->where('status', 'success')
                    ->where(function($q) use ($user, $protocol) {
                        $q->where('metadata', 'LIKE', '%"username":"'.$user.'"%')
                          ->orWhere('description', 'LIKE', "Pembuatan VPN $protocol ($user) %Hari%");
                    })
                    ->latest()
                    ->first();

                if ($tx && $tx->amount > 0) {
                    $owner = \App\Models\User::find($acc->user_id);
                    if ($owner) {
                        $owner->balance += $tx->amount;
                        $owner->save();
                        
                        \App\Models\Transaction::create([
                            'reference' => 'REFUND-' . strtoupper(\Illuminate\Support\Str::random(10)),
                            'user_id' => $owner->id,
                            'type' => 'refund',
                            'amount' => $tx->amount,
                            'total_amount' => $tx->amount,
                            'status' => 'success',
                            'description' => "Refund Hapus VPN $protocol ($user) < 15 Menit"
                        ]);
                        
                        \App\Models\Notification::create([
                            'user_id' => $owner->id,
                            'type' => 'order',
                            'message' => "Akun VPN $protocol ($user) dihapus dalam batas 15 menit. Dana Rp " . number_format($tx->amount, 0, ',', '.') . " telah dikembalikan ke Saldo Akun."
                        ]);
                        $isRefunded = true;
                    }
                }
            }
            $acc->delete();
            
            if ($isRefunded) {
                return back()->with('sweet_success', "Akun $user berhasil dihapus dan saldo telah direfund ke akun Anda.");
            }
        }

        return back()->with('sweet_success', "Akun $user berhasil dihapus.");
    }

    public function checkUsername(Request $request)
    {
        $username = $request->query('username');
        if (!$username) {
            return response()->json(['exists' => false]);
        }

        // Check SQLite
        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); r=c.execute(\"SELECT count(*) FROM account_registry WHERE username='{$username}'\").fetchone()[0]; print(r)";
        $dbRes = $this->runPython($dbScript);
        $inDb = intval(trim($dbRes['output'])) > 0;

        // Check Xray config.json
        $resXray = $this->vpn->executeBash("grep -E '^### $username |^#& $username |^#! $username |^#!# $username ' /etc/xray/config.json && echo 1 || echo 0");
        $xrayOut = explode("\n", trim($resXray['output']));
        $inXray = intval(end($xrayOut)) === 1;

        // Check SSH
        $resSsh = $this->vpn->executeBash("id -u $username >/dev/null 2>&1 && echo 1 || echo 0");
        $sshOut = explode("\n", trim($resSsh['output']));
        $inSsh = intval(end($sshOut)) === 1;

        return response()->json([
            'exists' => ($inDb || $inXray || $inSsh)
        ]);
    }
}
