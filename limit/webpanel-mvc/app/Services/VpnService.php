<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class VpnService
{
    protected $apiUrl;
    protected $secret;

    public function __construct()
    {
        $this->apiUrl = env('PYTHON_API_URL', 'http://127.0.0.1:1014/api/execute');
        $this->secret = env('INTERNAL_API_SECRET', 'secret123'); // Adjust if needed
    }

    /**
     * Executes a command via the Python API
     *
     * @param string $command The main command (e.g., 'addws')
     * @param array $args Arguments for the command
     * @return array ['success' => bool, 'output' => string, 'error' => string]
     */
    public function execute($command, $args = [])
    {
        try {
            $response = \Illuminate\Support\Facades\Http::timeout(60)->post($this->apiUrl, [
                'command' => $command,
                'args' => $args
            ]);

            if ($response->successful() && $response->json('ok')) {
                return [
                    'success' => true,
                    'output' => $response->json('output', '') ?: $response->json('stdout', '')
                ];
            }

            return [
                'success' => false,
                'error' => 'HTTP Error: ' . $response->status()
            ];
        } catch (\Exception $e) {
            \Illuminate\Support\Facades\Log::error("VpnService Execution Failed: " . $e->getMessage());
            return [
                'success' => false,
                'output' => '',
                'error' => 'Connection to Python API failed.'
            ];
        }
    }

    public function executeBash($scriptContent)
    {
        return $this->execute('bash', ['-c', "export TERM=xterm; " . $scriptContent]);
    }

    public function getAccounts($service = null)
    {
        $script = <<<PYTHON
import sys, json, sqlite3
sys.path.insert(0, '/usr/bin/kyt')
from kyt import list_ssh_system_accounts, list_xray_system_accounts, list_suspended_accounts

service = '$service'
accounts = []

try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.row_factory = sqlite3.Row
    db_rows = c.execute("SELECT * FROM account_registry").fetchall()
    db_map = { f"{r['service']}_{r['username']}": dict(r) for r in db_rows }
    c.close()
except:
    db_map = {}

if service == 'ssh' or not service:
    for a in list_ssh_system_accounts():
        k = f"ssh_{a['username']}"
        db_info = db_map.get(k, {})
        a['active'] = 0 if a.get('status') == 'suspended' or a.get('status') == 'L' else 1
        a['created_at'] = db_info.get('created_at', '')
        accounts.append(a)

xray_services = ['vmess', 'vless', 'trojan', 'shadowsocks']
services_to_fetch = [service] if service in xray_services else (xray_services if not service else [])

for svc in services_to_fetch:
    susp = {s['username']: s for s in list_suspended_accounts(svc)}
    for a in list_xray_system_accounts(svc):
        k = f"{svc}_{a['username']}"
        db_info = db_map.get(k, {})
        a['active'] = 0 if a['username'] in susp else 1
        a['created_at'] = db_info.get('created_at', '')
        accounts.append(a)

print(json.dumps(accounts))
PYTHON;

        $res = $this->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);
        if ($res['success']) {
            return json_decode($res['output'], true) ?? [];
        }
        return [];
    }

    public function getAccountConfig($service, $username)
    {
        $script = "import sys; sys.path.insert(0, '/usr/bin/kyt'); from kyt import account_detail_text; print(account_detail_text('{$service}', '{$username}'))";
        $res = $this->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);
        return $res['success'] ? $res['output'] : "Failed to fetch config.";
    }

    public function registerAccountToDb($tg_id, $service, $username, $expiredDays, $isTrial = false)
    {
        $later = date('Y-m-d', strtotime("+$expiredDays days"));
        $isTrialStr = $isTrial ? 'True' : 'False';
        $script = "import sys; sys.path.insert(0, '/usr/bin/kyt'); from kyt import register_account_creation; register_account_creation('{$tg_id}', '{$service}', '{$username}', '{$later}', is_trial={$isTrialStr})";
        return $this->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);
    }

    /**
     * Helper to run awk or grep commands for counting
     */
    public function count($command, $divisor = 1)
    {
        // For simple commands like `awk ... /etc/passwd`, we need to run them in a shell wrapper
        // because subprocess.run takes raw commands, not shell strings by default in our python api unless shell=True
        // Actually, the python API does `subprocess.run([command] + args)`.
        // So we can pass `bash` as command, and `-c` and `$command` as args.
        $res = $this->execute('bash', ['-c', $command]);
        
        if ($res['success']) {
            $val = intval(trim($res['output']));
            if ($divisor > 1) {
                $val = floor($val / $divisor);
            }
            return max(0, $val);
        }
        
        return 0;
    }
}
