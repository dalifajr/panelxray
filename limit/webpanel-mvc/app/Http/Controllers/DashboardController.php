<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\VpnService;

class DashboardController extends Controller
{
    public function index(VpnService $vpn)
    {
        $authUser = auth()->user();
        
        if ($authUser->role === 'customer') {
            $sshCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->where('service', 'ssh')->count();
            $vmsCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->where('service', 'vmess')->count();
            $vlsCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->where('service', 'vless')->count();
            $trjCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->where('service', 'trojan')->count();
            $ssnCount = \App\Models\VpnAccount::where('user_id', $authUser->id)->where('service', 'shadowsocks')->count();
        } else {
            // Fetch accurate stats matching the Telegram Bot for admin
            $sshCount = $vpn->count("awk -F: '$3>=1000 && $1!=\"nobody\" {c++} END{print c+0}' /etc/passwd 2>/dev/null");
            $vmsCount = $vpn->count("grep -c -E '^### ' /etc/xray/config.json 2>/dev/null", 2);
            $vlsCount = $vpn->count("grep -c -E '^#& ' /etc/xray/config.json 2>/dev/null", 2);
            $trjCount = $vpn->count("grep -c -E '^#! ' /etc/xray/config.json 2>/dev/null", 2);
            $ssnCount = $vpn->count("grep -c -E '^#!# ' /etc/xray/config.json 2>/dev/null", 2);
        }

        return view('dashboard', compact('sshCount', 'vmsCount', 'vlsCount', 'trjCount', 'ssnCount'));
    }
}
