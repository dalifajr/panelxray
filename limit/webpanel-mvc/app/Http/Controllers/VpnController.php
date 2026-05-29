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
        
        return view('vpn.list', compact('protocol', 'parsedUsers'));
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

        return view('vpn.create', compact('protocol'));
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
            'quota' => 'nullable|integer|min:0'
        ]);

        $userStr = $validated['username'];
        $exp = $validated['expired'];
        $pw = $validated['password'] ?? '1';
        $ip = $validated['limit_ip'] ?? '1';
        $sni = $validated['sni_config'] ?? '3';
        $quota = $validated['quota'] ?? '0';

        $authUser = auth()->user();

        // Cek limit pembuatan akun bagi customer
        if ($authUser->role === 'customer') {
            $activeCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->count();
            if ($activeCount >= $authUser->vpn_account_limit) {
                return back()->with('sweet_error', "Gagal membuat akun: Anda telah mencapai batas maksimal pembuatan akun VPN ({$authUser->vpn_account_limit} akun aktif).")->withInput();
            }
            // Customer dipaksa limit IP 1
            $ip = '1';
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
            // Register to SQLite database
            $tgId = auth()->user()->telegram_id ?? '0';
            $this->vpn->registerAccountToDb($tgId, $protocol, $userStr, $exp, false);
            
            // Catat kepemilikan di database Laravel
            \App\Models\VpnAccount::create([
                'user_id' => auth()->id(),
                'vpn_username' => $userStr,
                'service' => $protocol
            ]);

            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $userStr berhasil dibuat!");
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

        return view('vpn.renew', compact('protocol', 'user', 'quota', 'limit_ip'));
    }

    public function renew(Request $request, $protocol, $user)
    {
        $authUser = auth()->user();
        if ($authUser->role === 'customer') {
            $owns = \App\Models\VpnAccount::where('user_id', $authUser->id)
                ->where('service', $protocol)
                ->where('vpn_username', $user)
                ->exists();
            if (!$owns) abort(403, 'Unauthorized action.');
        }

        $validated = $request->validate([
            'days' => 'required|integer|min:1|max:365',
            'quota' => 'nullable|integer|min:0',
            'limit_ip' => 'nullable|integer|min:1'
        ]);
        
        $days = $validated['days'];
        $quota = $validated['quota'] ?? 0;
        $limit_ip = $validated['limit_ip'] ?? 1;

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
        
        // Remove from local vpn_accounts tracking
        \App\Models\VpnAccount::where('vpn_username', $user)->where('service', $protocol)->delete();

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
