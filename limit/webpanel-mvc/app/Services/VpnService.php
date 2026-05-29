<?php

namespace App\Services;

use Illuminate\Support\Facades\Log;

class VpnService
{
    const BRIDGE_SOCK = '/tmp/vpn-bridge.sock';

    public function __construct()
    {
        // No longer needs API URL — uses Unix socket bridge
    }

    /**
     * Send a command to the VPN Bridge service via Unix socket.
     *
     * @param string $cmd  The raw command/script string
     * @param string $mode 'bash' or 'python'
     * @param string|null $stdin Optional stdin data to pipe into the command
     * @return array ['success' => bool, 'output' => string, 'error' => string]
     */
    private function bridge($cmd, $mode = 'bash', $stdin = null)
    {
        $payload = json_encode([
            'cmd' => base64_encode($cmd),
            'mode' => $mode,
            'stdin' => $stdin ? base64_encode($stdin) : '',
        ]);

        $sock = @stream_socket_client('unix://' . self::BRIDGE_SOCK, $errno, $errstr, 10);
        if (!$sock) {
            Log::error("Bridge connect failed: [$errno] $errstr");
            return [
                'success' => false,
                'output' => '',
                'error' => "Bridge unavailable: $errstr"
            ];
        }

        // Send request
        fwrite($sock, $payload);
        stream_socket_shutdown($sock, STREAM_SHUT_WR);  // Signal end of request

        // Read response
        $response = stream_get_contents($sock);
        fclose($sock);

        $result = json_decode($response, true);
        if (!$result) {
            Log::error("Bridge invalid response: " . substr($response, 0, 200));
            return [
                'success' => false,
                'output' => '',
                'error' => 'Invalid bridge response'
            ];
        }

        $output = trim($result['stdout'] ?? '');
        $stderr = trim($result['stderr'] ?? '');
        $rc = $result['rc'] ?? -1;

        Log::info("Bridge [$mode] rc=$rc output=" . substr($output, 0, 500));
        if ($stderr) {
            Log::info("Bridge stderr: " . substr($stderr, 0, 300));
        }

        return [
            'success' => ($rc === 0),
            'output' => $output,
            'error' => ($rc !== 0) ? "Exit $rc: $stderr" : ''
        ];
    }

    /**
     * Execute a bash script via the bridge.
     */
    public function executeBash($scriptContent)
    {
        return $this->bridge($scriptContent, 'bash');
    }

    /**
     * Execute a bash command with stdin data piped in.
     */
    public function executeBashWithStdin($cmd, $stdinData)
    {
        return $this->bridge($cmd, 'bash', $stdinData);
    }

    /**
     * Execute a Python script via the bridge.
     */
    public function runPython($script)
    {
        return $this->bridge($script, 'python');
    }

    /**
     * Legacy execute method — now routes through executeBash.
     */
    public function execute($command, $args = [])
    {
        $cmdString = $command;
        foreach ($args as $arg) {
            $cmdString .= ' ' . escapeshellarg($arg);
        }
        return $this->executeBash($cmdString);
    }

    public function getAccounts($service = null)
    {
        // Fetch all accounts from SQLite database
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
        $resDb = $this->runPython($pythonScript);
        $dbRows = json_decode(trim($resDb['output']), true) ?? [];
        
        $dbMap = [];
        foreach ($dbRows as $r) {
            if (isset($r['service']) && isset($r['username'])) {
                $dbMap[$r['service'] . '_' . $r['username']] = $r;
            }
        }

        $accounts = [];

        if ($service === 'ssh' || !$service) {
            $resSsh = $this->executeBash("awk -F: '\$3>=1000 && \$1!=\"nobody\" {print \$1}' /etc/passwd");
            $sshOutput = array_filter(explode("\n", $resSsh['output']));
            
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
                $grepCmd = "grep -E '^" . preg_quote($marker) . " ' /etc/xray/config.json | awk '{print \$2, \$3}'";
                $resXray = $this->executeBash($grepCmd);
                $lines = array_filter(explode("\n", $resXray['output']));
                
                $resSusp = $this->executeBash("ls -1 /etc/kyt/suspended/{$svc} 2>/dev/null");
                $suspendedOutput = array_filter(explode("\n", $resSusp['output']));
                $suspendedSvc = array_flip(array_map('trim', $suspendedOutput));

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
                        'active' => 1, // Since they are in config.json, they are active
                        'created_at' => $dbInfo['created_at'] ?? '',
                        'expires_at' => $parts[1] ?? ($dbInfo['expires_at'] ?? '')
                    ];
                }

                // Add suspended users who are missing from config.json
                foreach (array_keys($suspendedSvc) as $user) {
                    if (empty($user)) continue;
                    if (isset($seen[$user])) continue;
                    $seen[$user] = true;

                    $k = "{$svc}_{$user}";
                    $dbInfo = $dbMap[$k] ?? [];

                    // Try to read expiry from the suspended file
                    $resExp = $this->executeBash("awk '{print \$1}' /etc/kyt/suspended/{$svc}/{$user} 2>/dev/null");
                    $suspExp = trim($resExp['output']);

                    $accounts[] = [
                        'service' => $svc,
                        'username' => $user,
                        'active' => 0, // They are suspended
                        'created_at' => $dbInfo['created_at'] ?? '',
                        'expires_at' => $suspExp ?: ($dbInfo['expires_at'] ?? '')
                    ];
                }
            }
        }

        return $accounts;
    }

    public function getAccountConfig($service, $username)
    {
        $script = "import sys, os; sys.stderr = open(os.devnull, 'w'); sys.path.insert(0, '/usr/bin'); from kyt import account_detail_text; print(account_detail_text('{$service}', '{$username}'))";
        $res = $this->runPython($script);
        return $res['success'] ? $res['output'] : "Failed to fetch config.";
    }

    public function registerAccountToDb($tg_id, $service, $username, $expiredDays, $isTrial = false)
    {
        $later = date('Y-m-d', strtotime("+$expiredDays days"));
        $isTrialStr = $isTrial ? '1' : '0';
        $script = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute(\"INSERT OR REPLACE INTO account_registry (tg_id, service, username, is_trial, created_at, expires_at) VALUES ('{$tg_id}', '{$service}', '{$username}', {$isTrialStr}, date('now'), '{$later}')\"); c.commit(); print('OK')";
        return $this->runPython($script);
    }

    /**
     * Helper to run awk or grep commands for counting
     */
    public function count($command, $divisor = 1)
    {
        $res = $this->executeBash($command);
        
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
