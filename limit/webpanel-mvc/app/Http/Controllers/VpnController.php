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

        // Fetch users using bash commands
        $users = [];
        if ($protocol === 'ssh') {
            $res = $this->vpn->execute('bot-member-ssh');
            $rawList = $res['success'] ? $res['output'] : '';
        } else {
            $cmd = 'bot-member-' . ($protocol === 'shadowsocks' ? 'ss' : $protocol);
            $res = $this->vpn->execute($cmd);
            $rawList = $res['success'] ? $res['output'] : '';
        }

        $parsedUsers = [];
        $lines = explode("\n", $rawList);
        $current = [];
        foreach ($lines as $line) {
            $line = trim($line);
            if (preg_match('/Username\s*:\s*(.+)/i', $line, $m) || preg_match('/Akun\s*:\s*(.+)/i', $line, $m)) {
                $current['username'] = trim($m[1]);
            }
            if (preg_match('/Expired\s*:\s*(.+)/i', $line, $m) || preg_match('/Exp\s*:\s*(.+)/i', $line, $m)) {
                $current['expired'] = trim($m[1]);
                if (isset($current['username'])) {
                    $parsedUsers[] = $current;
                }
                $current = []; // Reset for next user
            }
        }

        return view('vpn.list', compact('protocol', 'rawList', 'parsedUsers'));
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
            $res = $this->vpn->execute('bash', ['-c', "useradd -e $later -s /bin/false -M $user && echo \"$user:$pw\" | chpasswd"]);
            if ($res['success']) {
                $this->vpn->execute('bash', ['-c', "mkdir -p /etc/kyt/limit/ssh/ip && echo \"$ip\" > /etc/kyt/limit/ssh/ip/$user"]);
            }
        } elseif ($protocol === 'vmess') {
            $res = $this->vpn->execute('addws', ['none', $user, $exp, $pw, $ip]);
        } elseif ($protocol === 'vless') {
            $res = $this->vpn->execute('addvless', ['none', $user, $exp, $pw, $ip]);
        } elseif ($protocol === 'trojan') {
            $res = $this->vpn->execute('addtrojan', ['none', $user, $exp, $pw, $ip]);
        } elseif ($protocol === 'shadowsocks') {
            $res = $this->vpn->execute('addss', ['none', $user, $exp, $pw, $ip]);
        }

        if ($res && $res['success']) {
            return redirect()->route('vpn.index', $protocol)->with('success', "Akun $user berhasil dibuat. \n" . $res['output']);
        }

        return back()->with('error', 'Gagal membuat akun: ' . ($res['error'] ?? 'Unknown error'))->withInput();
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
            $res = $this->vpn->execute('bash', ['-c', "usermod -e $later $user && passwd -u $user"]);
        } else {
            $cmd = 'renew' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->execute($cmd, [$user, $days]);
        }

        if ($res['success']) {
            return redirect()->route('vpn.index', $protocol)->with('success', "Akun $user berhasil diperpanjang.");
        }
        return back()->with('error', 'Gagal perpanjang: ' . $res['error']);
    }

    public function suspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->execute('suspssh', [$user]);
        } else {
            $cmd = 'susp' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->execute($cmd, [$user]);
        }
        return back()->with('success', "Akun $user disuspend.");
    }

    public function unsuspend($protocol, $user)
    {
        if ($protocol === 'ssh') {
            $res = $this->vpn->execute('unsuspssh', [$user]);
        } else {
            $cmd = 'unsusp' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->execute($cmd, [$user]);
        }
        return back()->with('success', "Akun $user diaktifkan kembali.");
    }

    public function delete($protocol, $user)
    {
        if ($protocol === 'ssh') {
            // Note: the bash script 'delssh' might expect input from stdin.
            // Let's use userdel directly to be safe, or printf
            $res = $this->vpn->execute('bash', ['-c', "printf '%s\n' '$user' | delssh"]);
            if (!$res['success']) {
                $res = $this->vpn->execute('userdel', ['-f', $user]);
            }
        } else {
            $cmd = 'del' . ($protocol === 'shadowsocks' ? 'ss' : ($protocol === 'vmess' ? 'ws' : $protocol));
            $res = $this->vpn->execute($cmd, [$user]);
        }
        return back()->with('success', "Akun $user berhasil dihapus.");
    }
}
