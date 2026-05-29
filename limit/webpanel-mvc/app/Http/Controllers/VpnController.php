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

        $user = $validated['username'];
        $exp = $validated['expired'];
        $pw = $validated['password'] ?? '1';
        $ip = $validated['limit_ip'] ?? '1';
        $sni = $validated['sni_config'] ?? '3';
        $quota = $validated['quota'] ?? '0';

        $res = null;

        if ($protocol === 'ssh') {
            // SSH creation (useradd)
            $later = date('Y-m-d', strtotime("+$exp days"));
            $res = $this->vpn->executeBash("useradd -e $later -s /bin/false -M $user && echo \"$user:$pw\" | chpasswd");
            if ($res['success']) {
                $this->vpn->executeBash("mkdir -p /etc/kyt/limit/ssh/ip && echo \"$ip\" > /etc/kyt/limit/ssh/ip/$user");
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
            $inputLines = [$sni, $user, $exp, $quota, $ip];

            Log::info("CREATE: Piping to $cmd with inputs: " . json_encode($inputLines));
            $res = $this->pipeInputToCommand($inputLines, $cmd);
            Log::info("CREATE result: code={$res['success']}, output=" . substr($res['output'], 0, 500));
        }

        if ($res && $res['success']) {
            // Register to SQLite database
            $tgId = auth()->user()->email ? explode('@', auth()->user()->email)[0] : '0';
            $this->vpn->registerAccountToDb($tgId, $protocol, $user, $exp, false);
            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $user berhasil dibuat!");
        }

        return back()->with('sweet_error', 'Gagal membuat akun: ' . ($res['error'] ?? $res['output'] ?? 'Unknown error'))->withInput();
    }

    public function renewForm($protocol, $user)
    {
        return view('vpn.renew', compact('protocol', 'user'));
    }

    public function renew(Request $request, $protocol, $user)
    {
        $validated = $request->validate([
            'days' => 'required|integer|min:1|max:365'
        ]);
        
        $days = $validated['days'];

        if ($protocol === 'ssh') {
            $later = date('Y-m-d', strtotime("+$days days"));
            $res = $this->vpn->executeBash("usermod -e $later $user && passwd -u $user");
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

try:
    with open(path, 'r') as f:
        lines = f.readlines()
    changed = False
    next_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
            next_lines.append(f"{marker} {username} {new_expiry}\n")
            changed = True
        else:
            next_lines.append(line)
    if changed:
        with open(path, 'w') as f:
            f.writelines(next_lines)
        os.system('systemctl restart xray >/dev/null 2>&1')
        print("SUCCESS")
except Exception as e:
    pass
PYTHON;
            $res = $this->runPython($script);
            // Ensure success is set correctly based on python output
            $res['success'] = strpos($res['output'], 'SUCCESS') !== false;
        }

        if ($res['success']) {
            // Update SQLite DB
            $later = date('Y-m-d', strtotime("+$days days"));
            $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET expires_at='{$later}' WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
            $this->runPython($dbScript);

            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $user berhasil diperpanjang.");
        }
        return back()->with('sweet_error', 'Gagal perpanjang: ' . $res['error']);
    }

    public function suspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -L $user");
        } else {
            $res = $this->vpn->executeBash("mkdir -p /etc/kyt/suspended/{$protocol} && touch /etc/kyt/suspended/{$protocol}/{$user} && systemctl restart xray >/dev/null 2>&1");
        }

        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET updated_at=date('now') WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $this->runPython($dbScript);

        return back()->with('sweet_success', "Akun $user disuspend.");
    }

    public function unsuspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -U $user");
        } else {
            $res = $this->vpn->executeBash("rm -f /etc/kyt/suspended/{$protocol}/{$user} && systemctl restart xray >/dev/null 2>&1");
        }

        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=1 WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $this->runPython($dbScript);

        return back()->with('sweet_success', "Akun $user diaktifkan kembali.");
    }

    public function delete($protocol, $user)
    {
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
        
        # Clean up cache and limit files
        srv = protocol
        os.system(f"rm -rf /etc/kyt/limit/{srv}/ip/{username}")
        os.system(f"rm -rf /etc/{srv}/{username}")
        os.system(f"sed -i '/\\b{username}\\b/d' /etc/{srv}/.{srv}.db 2>/dev/null")
        os.system(f"rm -f /etc/kyt/suspended/{srv}/{username}")
        
        print("SUCCESS")
    else:
        print("NOT_FOUND")
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

        return back()->with('sweet_success', "Akun $user berhasil dihapus.");
    }
}
