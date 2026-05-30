<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

use Illuminate\Support\Facades\Schedule;
use Illuminate\Support\Facades\Log;
use App\Models\VpnAccount;
use App\Services\VpnService;

Schedule::call(function () {
    $vpnService = app(VpnService::class);

    // 1. Suspend expired trials (created > 15 mins ago, not suspended yet)
    $trialsToSuspend = VpnAccount::where('is_trial', true)
        ->where('admin_suspended', false)
        ->where('created_at', '<=', now()->subMinutes(15))
        ->get();

    foreach ($trialsToSuspend as $acc) {
        $protocol = $acc->service;
        $user = $acc->vpn_username;
        
        Log::info("Trial scheduler: Suspending $protocol $user (Expired trial)");

        if ($protocol === 'ssh') {
            $vpnService->executeBash("usermod -L $user");
        } else {
            $scriptMap = ['vmess' => 'suspws', 'vless' => 'suspvless', 'trojan' => 'susptr', 'shadowsocks' => 'suspss'];
            $cmd = $scriptMap[$protocol] ?? 'suspws';
            $vpnService->executeBash("$cmd --user $user --reason trial_expired");
        }
        
        // Update SQLite DB
        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"UPDATE account_registry SET active=0 WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $vpnService->executeBashWithStdin("python3 -", $dbScript);

        // Update Laravel DB
        $acc->admin_suspended = true;
        $acc->save();
    }

    // 2. Delete trial accounts suspended for more than 1 day
    $trialsToDelete = VpnAccount::where('is_trial', true)
        ->where('admin_suspended', true)
        ->where('updated_at', '<=', now()->subDay())
        ->get();

    foreach ($trialsToDelete as $acc) {
        $protocol = $acc->service;
        $user = $acc->vpn_username;
        
        Log::info("Trial scheduler: Deleting $protocol $user (Trial suspended > 1 day)");

        if ($protocol === 'ssh') {
            $vpnService->executeBash("userdel -f $user 2>/dev/null; rm -f /etc/kyt/limit/ssh/ip/$user");
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
        
    srv = protocol
    os.system(f"rm -f /etc/kyt/suspended/{srv}/{username}")
    os.system(f"rm -rf /etc/kyt/limit/{srv}/ip/{username}")
    os.system(f"rm -rf /etc/{srv}/{username}")
    os.system(f"sed -i '/\\\\b{username}\\\\b/d' /etc/{srv}/.{srv}.db 2>/dev/null")
except Exception as e:
    pass
PYTHON;
            $vpnService->executeBashWithStdin("python3 -", $script);
        }

        // Clean from SQLite DB
        $dbScript = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"DELETE FROM account_registry WHERE service='{$protocol}' AND username='{$user}'\"); c.commit()";
        $vpnService->executeBashWithStdin("python3 -", $dbScript);
        
        // Remove from local vpn_accounts tracking
        $acc->delete();
    }
})->everyMinute();
