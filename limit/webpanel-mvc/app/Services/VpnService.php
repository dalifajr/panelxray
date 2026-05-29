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
import sqlite3, json, os, glob

ip_limits = {}
for path in glob.glob('/etc/kyt/limit/*/ip/*'):
    parts = path.split('/')
    if len(parts) >= 7:
        svc = parts[4]
        user = parts[6]
        try:
            with open(path, 'r') as f:
                val = f.read().strip()
                if val:
                    ip_limits[f"{svc}_{user}"] = int(val)
        except:
            pass

try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.row_factory = sqlite3.Row
    db_rows = c.execute("SELECT * FROM account_registry").fetchall()
    print(json.dumps({
        'db': [dict(r) for r in db_rows],
        'ip_limits': ip_limits
    }))
except Exception as e:
    print(json.dumps({'db': [], 'ip_limits': ip_limits}))
PYTHON;
        $resDb = $this->runPython($pythonScript);
        $parsed = json_decode(trim($resDb['output']), true) ?? ['db' => [], 'ip_limits' => []];
        $dbRows = $parsed['db'] ?? [];
        $ipLimits = $parsed['ip_limits'] ?? [];
        
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
                    'expires_at' => $dbInfo['expires_at'] ?? '',
                    'ip_limit' => $ipLimits["ssh_{$user}"] ?? 1
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
                        'expires_at' => $parts[1] ?? ($dbInfo['expires_at'] ?? ''),
                        'ip_limit' => $ipLimits["{$svc}_{$user}"] ?? 1
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
                        'expires_at' => $suspExp ?: ($dbInfo['expires_at'] ?? ''),
                        'ip_limit' => $ipLimits["{$svc}_{$user}"] ?? 1
                    ];
                }
            }
        }

        return $accounts;
    }

    public function getAccountConfig($service, $username)
    {
        $xrayMarkers = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
        $marker = $xrayMarkers[$service] ?? '###';
        
        $script = <<<PYTHON
import json
import os

try:
    with open('/etc/xray/domain', 'r') as f:
        domain = f.read().strip()
except:
    domain = ''

uuid = ''
quota = '0'
ip_limit = '1'

try:
    # Read UUID from config.json
    with open('/etc/xray/config.json', 'r') as f:
        lines = f.readlines()
        
    found_user = False
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == '$marker' and parts[1] == '$username':
            found_user = True
            # The next line contains the UUID in JSON format
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line.endswith(','):
                    next_line = next_line[:-1]
                try:
                    obj = json.loads("{" + next_line + "}")
                    if 'id' in obj:
                        uuid = obj['id']
                    elif 'password' in obj:
                        uuid = obj['password']
                except:
                    # Fallback regex extraction
                    import re
                    m = re.search(r'"(id|password)":\s*"([^"]+)"', next_line)
                    if m:
                        uuid = m.group(2)
            break
            
    # Read Quota
    try:
        with open(f'/etc/{service}/{username}', 'r') as f:
            val = int(f.read().strip())
            quota = str(val // (1024*1024*1024))
    except:
        quota = 'Unlimited'
        
    # Read IP limit
    try:
        with open(f'/etc/kyt/limit/{service}/ip/{username}', 'r') as f:
            ip_limit = f.read().strip()
    except:
        ip_limit = '1'

    print(json.dumps({
        'success': True,
        'domain': domain,
        'uuid': uuid,
        'quota': quota,
        'ip_limit': ip_limit,
        'username': '$username',
        'service': '$service'
    }))
except Exception as e:
    print(json.dumps({'success': False, 'error': str(e)}))
PYTHON;
        $res = $this->runPython($script);
        if ($res['success']) {
            return json_decode($res['output'], true);
        }
        return ['success' => false];
    }

    public function registerAccountToDb($tg_id, $service, $username, $expiredDays, $isTrial = false)
    {
        $later = date('Y-m-d', strtotime("+$expiredDays days"));
        $isTrialStr = $isTrial ? '1' : '0';
        $category = ($service === 'ssh') ? 'ssh' : 'xray';
        $script = <<<PYTHON
import sqlite3
import sys
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.execute(
        "INSERT OR REPLACE INTO account_registry (tg_id, service, category, username, is_trial, created_at, expires_at, active) "
        "VALUES ('{$tg_id}', '{$service}', '{$category}', '{$username}', {$isTrialStr}, date('now', 'localtime'), '{$later}', 1)"
    )
    c.commit()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
PYTHON;
        $res = $this->runPython($script);
        if (strpos($res['output'], 'ERROR:') !== false) {
            \Illuminate\Support\Facades\Log::error("Failed to register account to DB: " . $res['output']);
        }
        return $res;
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
