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
            $res = $this->vpn->executeBash("addws none $user $exp $pw $ip");
        } elseif ($protocol === 'vless') {
            $res = $this->vpn->executeBash("addvless none $user $exp $pw $ip");
        } elseif ($protocol === 'trojan') {
            $res = $this->vpn->executeBash("addtrojan none $user $exp $pw $ip");
        } elseif ($protocol === 'shadowsocks') {
            $res = $this->vpn->executeBash("addss none $user $exp $pw $ip");
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
            $cmd = 'renew' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->executeBash("$cmd $user $days");
        }

        if ($res['success']) {
            // Tell Bot to update DB
            $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import update_account_expiry; update_account_expiry('{$protocol}', '{$user}', '".date('Y-m-d', strtotime("+$days days"))."')";
            $this->vpn->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);

            return redirect()->route('vpn.index', $protocol)->with('sweet_success', "Akun $user berhasil diperpanjang.");
        }
        return back()->with('sweet_error', 'Gagal perpanjang: ' . $res['error']);
    }

    public function suspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("suspssh $user");
        } else {
            $cmd = 'susp' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->executeBash("$cmd $user");
        }
        
        $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import mark_account_inactive; mark_account_inactive('{$protocol}', '{$user}')";
        $this->vpn->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);

        return back()->with('sweet_success', "Akun $user disuspend.");
    }

    public function unsuspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("unsuspssh $user");
        } else {
            $cmd = 'unsusp' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->executeBash("$cmd $user");
        }

        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=1 WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $this->vpn->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);

        return back()->with('sweet_success', "Akun $user diaktifkan kembali.");
    }

    public function delete($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("printf '%s\n' '$user' | delssh");
            if (!$res['success']) {
                $res = $this->vpn->executeBash("userdel -f $user");
            }
        } else {
            $cmd = 'del' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->executeBash("$cmd $user");
        }

        $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import get_db; db=get_db(); db.execute('DELETE FROM account_registry WHERE service=? AND username=?', ('{$protocol}', '{$user}')); db.commit(); db.close()";
        $this->vpn->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);

        return back()->with('sweet_success', "Akun $user berhasil dihapus.");
    }
}
