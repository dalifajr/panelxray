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
        $cmdString = escapeshellcmd($command);
        foreach ($args as $arg) {
            $cmdString .= ' ' . escapeshellarg($arg);
        }
        
        // Execute via sudo directly without mixing stderr so JSON parses correctly
        $fullCommand = "sudo bash -c " . escapeshellarg("export PATH=\$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/kyt; export TERM=xterm; " . $cmdString);
        
        $output = [];
        $returnCode = 0;
        
        exec($fullCommand, $output, $returnCode);
        $outputStr = implode("\n", $output);
        
        Log::info("Executing CMD: " . $fullCommand);
        Log::info("Return Code: " . $returnCode);
        Log::info("Output: " . $outputStr);
        
        // The old Python API returned {ok: True, stdout: output} regardless of the exit code.
        return [
            'success' => true,
            'output' => $outputStr,
            'error' => ''
        ];
    }

    public function executeBash($scriptContent)
    {
        $b64 = base64_encode("export TERM=xterm; " . $scriptContent);
        return $this->execute('bash', ['-c', "echo '$b64' | base64 -d | bash"]);
    }

    public function getAccounts($service = null)
    {
        // Fetch all accounts from SQLite database using a tiny inline python script
        $pythonScript = <<<PYTHON
import sqlite3, json
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.row_factory = sqlite3.Row
    db_rows = c.execute("SELECT * FROM account_registry").fetchall()
    print(json.dumps([dict(r) for r in db_rows]))
except Exception as e:
    print("[]")
PYTHON;
        $b64 = base64_encode($pythonScript);
        $resDb = $this->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");
        $dbRows = json_decode(trim($resDb['output']), true) ?? [];
        
        $dbMap = [];
        foreach ($dbRows as $r) {
            if (isset($r['service']) && isset($r['username'])) {
                $dbMap[$r['service'] . '_' . $r['username']] = $r;
            }
        }

        $accounts = [];

        if ($service === 'ssh' || !$service) {
            // Fetch SSH users using awk on /etc/passwd
            $resSsh = $this->executeBash("awk -F: '\$3>=1000 && \$1!=\"nobody\" {print \$1}' /etc/passwd");
            $sshOutput = array_filter(explode("\n", $resSsh['output']));
            
            // For suspended ssh users, check if password hash contains !
            $resSusp = $this->executeBash("awk -F: '\$2 ~ /^!/ {print \$1}' /etc/shadow");
            $suspendedOutput = array_filter(explode("\n", $resSusp['output']));
            $suspendedSsh = array_flip($suspendedOutput);
            
            foreach ($sshOutput as $user) {
                $user = trim($user);
                if (empty($user)) continue;
                $k = "ssh_$user";
                $dbInfo = $dbMap[$k] ?? [];
                
                $accounts[] = [
                    'service' => 'ssh',
                    'username' => $user,
                    'active' => isset($suspendedSsh[$user]) ? 0 : 1,
                    'created_at' => $dbInfo['created_at'] ?? '',
                    'expires_at' => $dbInfo['expires_at'] ?? ''
                ];
            }
        }

        $xrayServices = [
            'vmess' => '###',
            'vless' => '#&',
            'trojan' => '#!',
            'shadowsocks' => '#!#'
        ];
        $servicesToFetch = $service ? (isset($xrayServices[$service]) ? [$service => $xrayServices[$service]] : []) : $xrayServices;

        if (!empty($servicesToFetch)) {
            foreach ($servicesToFetch as $svc => $marker) {
                // Fetch Xray users from config.json magic comments
                $grepCmd = "grep -E '^" . preg_quote($marker) . " ' /etc/xray/config.json | awk '{print \$2, \$3}'";
                $resXray = $this->executeBash($grepCmd);
                $lines = array_filter(explode("\n", $resXray['output']));
                
                // Fetch suspended users by checking /etc/kyt/suspended/<service>/
                $resSusp = $this->executeBash("ls -1 /etc/kyt/suspended/{$svc} 2>/dev/null");
                $suspendedOutput = array_filter(explode("\n", $resSusp['output']));
                $suspendedSvc = array_flip(array_map('trim', $suspendedOutput));

                // A single user might have 2 markers in config.json, so keep track of added users
                $seen = [];

                foreach ($lines as $line) {
                    $parts = explode(" ", trim($line));
                    if (count($parts) < 1) continue;
                    $user = trim($parts[0]);
                    if (empty($user)) continue;
                    if (isset($seen[$user])) continue;
                    $seen[$user] = true;

                    $k = "{$svc}_{$user}";
                    $dbInfo = $dbMap[$k] ?? [];
                    
                    $accounts[] = [
                        'service' => $svc,
                        'username' => $user,
                        'active' => isset($suspendedSvc[$user]) ? 0 : 1,
                        'created_at' => $dbInfo['created_at'] ?? '',
                        'expires_at' => $parts[1] ?? ($dbInfo['expires_at'] ?? '')
                    ];
                }
            }
        }

        return $accounts;
    }

    public function getAccountConfig($service, $username)
    {
        $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import account_detail_text; print(account_detail_text('{$service}', '{$username}'))";
        $b64 = base64_encode($script);
        $res = $this->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");
        return $res['success'] ? $res['output'] : "Failed to fetch config.";
    }

    public function registerAccountToDb($tg_id, $service, $username, $expiredDays, $isTrial = false)
    {
        $later = date('Y-m-d', strtotime("+$expiredDays days"));
        $isTrialStr = $isTrial ? '1' : '0';
        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"INSERT INTO account_registry (tg_id, service, username, is_trial, created_at, expires_at) VALUES ('{$tg_id}', '{$service}', '{$username}', {$isTrialStr}, date('now'), '{$later}')\"); c.commit()";
        $b64 = base64_encode($script);
        return $this->executeBash("echo '$b64' | base64 -d | /usr/bin/kyt/.venv/bin/python");
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
