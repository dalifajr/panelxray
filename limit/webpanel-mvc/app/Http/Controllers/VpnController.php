<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\VpnService;

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

    public function store(Request $request, $protocol)
    {
        if (!in_array($protocol, $this->protocols)) {
            abort(404);
        }

        $validated = $request->validate([
            'username' => 'required|string|max:30|regex:/^[a-zA-Z0-9_.-]+$/',
            'password' => 'nullable|string|max:30', // Used by SSH, VMESS, etc.
            'limit_ip' => 'nullable|integer|min:1',
            'expired' => 'required|integer|min:1|max:365'
        ]);

        $user = $validated['username'];
        $exp = $validated['expired'];
        $pw = $validated['password'] ?? '1';
        $ip = $validated['limit_ip'] ?? '1';

        $res = null;

        if ($protocol === 'ssh') {
            // SSH creation (useradd)
            $later = date('Y-m-d', strtotime("+$exp days"));
            $res = $this->vpn->executeBash("useradd -e $later -s /bin/false -M $user && echo \"$user:$pw\" | chpasswd");
            if ($res['success']) {
                $this->vpn->executeBash("mkdir -p /etc/kyt/limit/ssh/ip && echo \"$ip\" > /etc/kyt/limit/ssh/ip/$user");
            }
        } elseif ($protocol === 'vmess') {
            $inputs = "3\\n$user\\n$exp\\n0\\n$ip\\n";
            $res = $this->vpn->executeBash("printf '$inputs' | addws");
        } elseif ($protocol === 'vless') {
            $inputs = "3\\n$user\\n$exp\\n0\\n$ip\\n";
            $res = $this->vpn->executeBash("printf '$inputs' | addvless");
        } elseif ($protocol === 'trojan') {
            $inputs = "3\\n$user\\n$exp\\n0\\n$ip\\n";
            $res = $this->vpn->executeBash("printf '$inputs' | addtr");
        } elseif ($protocol === 'shadowsocks') {
            $inputs = "3\\n$user\\n$exp\\n0\\n$ip\\n";
            $res = $this->vpn->executeBash("printf '$inputs' | addss");
        }

        if ($res && $res['success']) {
            $this->vpn->registerAccountToDb(auth()->user()->email ? explode('@', auth()->user()->email)[0] : '0', $protocol, $user, $exp, false);
            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $user berhasil dibuat!");
        }

        return back()->with('sweet_error', 'Gagal membuat akun: ' . ($res['error'] ?? 'Unknown error'))->withInput();
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
            next_lines.append(f"{marker} {username} {new_expiry}\\n")
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
            $b64 = base64_encode($script);
            $res = $this->vpn->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");
            // Ensure success is set correctly based on python output
            $res['success'] = strpos($res['output'], 'SUCCESS') !== false;
        }

        if ($res['success']) {
            // Tell Bot to update DB
            $later = date('Y-m-d', strtotime("+$days days"));
            $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET expires_at='{$later}' WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
            $this->vpn->executeBash("/usr/bin/kyt/.venv/bin/python -c " . escapeshellarg($script));

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
        // Web panel doesn't strictly need to run mark_account_inactive because suspend scripts usually handle it natively.
        // But to be thorough, we can execute an UPDATE.
        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET updated_at=date('now') WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $b64 = base64_encode($script);
        $this->vpn->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");

        return back()->with('sweet_success', "Akun $user disuspend.");
    }

    public function unsuspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -U $user");
        } else {
            $res = $this->vpn->executeBash("rm -f /etc/kyt/suspended/{$protocol}/{$user} && systemctl restart xray >/dev/null 2>&1");
        }

        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=1 WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $b64 = base64_encode($script);
        $this->vpn->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");

        return back()->with('sweet_success', "Akun $user diaktifkan kembali.");
    }

    public function delete($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("printf '%s\\n' '$user' | delssh");
            if (!$res['success']) {
                $res = $this->vpn->executeBash("userdel -f $user");
            }
        } else {
            $xrayMarkers = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
            $marker = $xrayMarkers[$protocol] ?? '###';
            
            $script = <<<PYTHON
import os
path = '/etc/xray/config.json'
marker = '$marker'
username = '$user'

try:
    with open(path, 'r') as f:
        lines = f.readlines()
    changed = False
    next_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            if line.lstrip().startswith("},{"):
                changed = True
                skip_next = False
                continue
            skip_next = False
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
            changed = True
            skip_next = True
            continue
        next_lines.append(line)
    if changed:
        with open(path, 'w') as f:
            f.writelines(next_lines)
        os.system('systemctl restart xray >/dev/null 2>&1')
        
        srv = 'vmess'
        if marker == '#&': srv = 'vless'
        elif marker == '#!': srv = 'trojan'
        elif marker == '#!#': srv = 'shadowsocks'
        
        os.system(f"rm -rf /etc/kyt/limit/{srv}/ip/{username}")
        os.system(f"rm -rf /etc/{srv}/{username}")
        os.system(f"sed -i '/\\\\b{username}\\\\b/d' /etc/{srv}/.{srv}.db 2>/dev/null")
        
        print("SUCCESS")
except Exception as e:
    pass
PYTHON;
            $b64 = base64_encode($script);
            $res = $this->vpn->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");
        }

        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"DELETE FROM account_registry WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $b64 = base64_encode($script);
        $this->vpn->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");

        return back()->with('sweet_success', "Akun $user berhasil dihapus.");
    }
}
