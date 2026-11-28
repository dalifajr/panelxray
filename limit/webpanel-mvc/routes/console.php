<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

use Illuminate\Support\Facades\Schedule;
use Illuminate\Support\Facades\Log;
use App\Models\VpnAccount;
use App\Services\VpnAccountManager;
use App\Services\VpnService;

Schedule::call(function () {
    $vpnService = app(VpnService::class);
    $vpnManager = app(VpnAccountManager::class);

    // 1. Suspend expired trials (created > 15 mins ago, not suspended yet)
    $trialsToSuspend = VpnAccount::where('is_trial', true)
        ->where('admin_suspended', false)
        ->where('created_at', '<=', now()->subMinutes(15))
        ->get();

    foreach ($trialsToSuspend as $acc) {
        $protocol = (string) $acc->service;
        $user = (string) $acc->vpn_username;
        $safeUser = escapeshellarg($user);

        Log::info("Trial scheduler: Suspending {$protocol} {$user} (Expired trial)");

        if ($protocol === 'ssh') {
            $vpnService->executeBash("suspssh --user {$safeUser} --reason trial_expired");
        } else {
            $scriptMap = ['vmess' => 'suspws', 'vless' => 'suspvless', 'trojan' => 'susptr', 'shadowsocks' => 'suspss'];
            $cmd = $scriptMap[$protocol] ?? 'suspws';
            $vpnService->executeBash("{$cmd} --user {$safeUser} --reason trial_expired");
        }

        $payloadB64 = base64_encode(json_encode(['service' => $protocol, 'username' => $user]));
        $dbScript = "import base64,json,sqlite3; d=json.loads(base64.b64decode('{$payloadB64}').decode()); c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute('UPDATE account_registry SET active=0 WHERE LOWER(service)=LOWER(?) AND LOWER(username)=LOWER(?)',(d['service'],d['username'])); c.commit()";
        $vpnService->executeBashWithStdin("python3 -", $dbScript);

        $acc->admin_suspended = true;
        $acc->save();
    }

    // 2. Delete trial accounts suspended for more than 1 day via VpnAccountManager (complete cleanup)
    $trialsToDelete = VpnAccount::where('is_trial', true)
        ->where('admin_suspended', true)
        ->where('updated_at', '<=', now()->subDay())
        ->get();

    foreach ($trialsToDelete as $acc) {
        $protocol = (string) $acc->service;
        $user = (string) $acc->vpn_username;

        Log::info("Trial scheduler: Deleting {$protocol} {$user} (Trial suspended > 1 day)");

        try {
            $vpnManager->deleteAccount($protocol, $user);
        } catch (\Throwable $e) {
            Log::warning("Trial scheduler delete fallback for {$protocol}/{$user}: " . $e->getMessage());
            $acc->delete();
        }
    }
})->everyMinute();

// 3. Reconcile VPS cron (xp / delexp / limit-ip) state back into Laravel vpn_accounts table
Schedule::call(function () {
    $vpnService = app(VpnService::class);
    $services = ['ssh', 'vmess', 'vless', 'trojan', 'shadowsocks'];

    foreach ($services as $svc) {
        try {
            $liveAccounts = $vpnService->getAccounts($svc);
        } catch (\Throwable $e) {
            continue;
        }
        $byUser = [];
        foreach ($liveAccounts as $row) {
            $u = strtolower((string) ($row['username'] ?? ''));
            if ($u !== '') {
                $byUser[$u] = $row;
            }
        }

        $tracked = VpnAccount::where('service', $svc)->get();
        foreach ($tracked as $acc) {
            $key = strtolower((string) $acc->vpn_username);
            if (!isset($byUser[$key])) {
                // Account was permanently deleted on VPS (e.g. xp 3-day grace elapsed)
                $acc->delete();
                continue;
            }
            $isSuspendedOnVps = !empty($byUser[$key]['suspended']) || !empty($byUser[$key]['expired_grace']);
            if ($isSuspendedOnVps && !$acc->admin_suspended) {
                $acc->admin_suspended = true;
                $acc->save();
            } elseif (!$isSuspendedOnVps && $acc->admin_suspended) {
                $acc->admin_suspended = false;
                $acc->save();
            }
        }
    }
})->everyFiveMinutes();
