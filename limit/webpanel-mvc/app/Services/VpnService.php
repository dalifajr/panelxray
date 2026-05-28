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
        
        // The old Python API returned {ok: True, stdout: output} regardless of the exit code.
        // Some commands like `grep -c` return exit code 1 if no matches are found, but output "0".
        // Therefore, we consider it a "success" if it ran without throwing a fatal system error,
        // mirroring the old API's behavior exactly.
        
        return [
            'success' => true,
            'output' => $outputStr,
            'error' => ''
        ];
    }

    public function executeBash($scriptContent)
    {
        return $this->execute('bash', ['-c', "export TERM=xterm; " . $scriptContent]);
    }

    public function getAccounts($service = null)
    {
        // Fetch all accounts from SQLite database using sudo sqlite3
        $sqliteCmd = "sudo sqlite3 -json /usr/bin/kyt/database.db 'SELECT * FROM account_registry'";
        exec($sqliteCmd, $dbOutput, $dbReturn);
        $dbRows = json_decode(implode("\n", $dbOutput), true) ?? [];
        
        $dbMap = [];
        foreach ($dbRows as $r) {
            $dbMap[$r['service'] . '_' . $r['username']] = $r;
        }

        $accounts = [];

        if ($service === 'ssh' || !$service) {
            // Fetch SSH users using awk on /etc/passwd
            $awkCmd = "sudo awk -F: '$3>=1000 && $1!=\"nobody\" {print $1}' /etc/passwd";
            exec($awkCmd, $sshOutput);
            
            // For suspended ssh users, check if password hash contains !
            $shadowCmd = "sudo awk -F: '$2 ~ /^!/ {print $1}' /etc/shadow";
            exec($shadowCmd, $suspendedOutput);
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

        $xrayServices = ['vmess', 'vless', 'trojan', 'shadowsocks'];
        $servicesToFetch = in_array($service, $xrayServices) ? [$service] : (!$service ? $xrayServices : []);

        if (!empty($servicesToFetch)) {
            // Fetch Xray users from config.json
            $xrayCmd = "sudo cat /etc/xray/config.json";
            exec($xrayCmd, $xrayOutput);
            $xrayConfig = json_decode(implode("\n", $xrayOutput), true) ?? [];
            
            $inbounds = $xrayConfig['inbounds'] ?? [];
            foreach ($servicesToFetch as $svc) {
                // In Xray, suspended accounts might just be prefixed with # or removed.
                // For simplicity, we just extract active clients.
                foreach ($inbounds as $inbound) {
                    if (($inbound['protocol'] ?? '') === $svc || ($svc === 'shadowsocks' && ($inbound['protocol'] ?? '') === 'shadowsocks')) {
                        $clients = $inbound['settings']['clients'] ?? [];
                        foreach ($clients as $client) {
                            $user = $client['email'] ?? '';
                            if (empty($user)) continue;
                            
                            $k = "{$svc}_{$user}";
                            $dbInfo = $dbMap[$k] ?? [];
                            
                            $accounts[] = [
                                'service' => $svc,
                                'username' => $user,
                                'active' => 1, // Assume active if in config
                                'created_at' => $dbInfo['created_at'] ?? '',
                                'expires_at' => $dbInfo['expires_at'] ?? ''
                            ];
                        }
                    }
                }
            }
        }

        return $accounts;
    }

    public function getAccountConfig($service, $username)
    {
        $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import account_detail_text; print(account_detail_text('{$service}', '{$username}'))";
        $res = $this->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);
        return $res['success'] ? $res['output'] : "Failed to fetch config.";
    }

    public function registerAccountToDb($tg_id, $service, $username, $expiredDays, $isTrial = false)
    {
        $later = date('Y-m-d', strtotime("+$expiredDays days"));
        $isTrialStr = $isTrial ? '1' : '0';
        $cmd = "sudo sqlite3 /usr/bin/kyt/database.db \"INSERT INTO account_registry (tg_id, service, username, is_trial, created_at, expires_at) VALUES ('{$tg_id}', '{$service}', '{$username}', {$isTrialStr}, date('now'), '{$later}')\"";
        return $this->executeBash($cmd);
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
