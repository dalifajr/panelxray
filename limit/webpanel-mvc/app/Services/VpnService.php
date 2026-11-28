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

        $errDetails = $stderr !== '' ? $stderr : $output;

        return [
            'success' => ($rc === 0),
            'output' => $output,
            'error' => ($rc !== 0) ? ("Exit $rc" . ($errDetails !== '' ? ": $errDetails" : '')) : ''
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
quotas = {}
suspended_meta = {}
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

for path in glob.glob('/etc/kyt/limit/*/quota/*'):
    parts = path.split('/')
    if len(parts) >= 7:
        svc = parts[4]
        user = parts[6]
        try:
            with open(path, 'r') as f:
                val = f.read().strip()
                if val:
                    quotas[f"{svc}_{user}"] = int(val)
        except:
            pass

for path in glob.glob('/etc/kyt/suspended/*/*'):
    parts = path.split('/')
    if len(parts) >= 6:
        svc = parts[4]
        user = parts[5]
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_line = f.readline().strip()
                toks = raw_line.split(None, 2)
                suspended_meta[f"{svc}_{user}"] = {
                    'exp': toks[0] if len(toks) >= 1 else '',
                    'reason': toks[2].strip() if len(toks) >= 3 else '',
                }
        except:
            pass

try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.row_factory = sqlite3.Row
    db_rows = c.execute("SELECT * FROM account_registry").fetchall()
    print(json.dumps({
        'db': [dict(r) for r in db_rows],
        'ip_limits': ip_limits,
        'quotas': quotas,
        'suspended_meta': suspended_meta
    }))
except Exception as e:
    print(json.dumps({'db': [], 'ip_limits': ip_limits, 'quotas': quotas, 'suspended_meta': suspended_meta}))
PYTHON;
        $resDb = $this->runPython($pythonScript);
        $parsed = json_decode(trim($resDb['output']), true) ?? ['db' => [], 'ip_limits' => [], 'quotas' => [], 'suspended_meta' => []];
        $dbRows = $parsed['db'] ?? [];
        $ipLimits = $parsed['ip_limits'] ?? [];
        $quotas = $parsed['quotas'] ?? [];
        $suspendedMeta = $parsed['suspended_meta'] ?? [];
        
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
                $meta = $suspendedMeta[$k] ?? null;
                $isSusp = isset($suspendedSsh[$user]) || is_array($meta);
                
                $accounts[] = [
                    'service' => 'ssh',
                    'username' => $user,
                    'active' => $isSusp ? 0 : 1,
                    'created_at' => $dbInfo['created_at'] ?? '',
                    'expires_at' => $dbInfo['expires_at'] ?? ($meta['exp'] ?? ''),
                    'ip_limit' => $ipLimits["ssh_{$user}"] ?? 1,
                    'quota' => $quotas["ssh_{$user}"] ?? 0,
                    'suspend_reason' => $isSusp ? (string) ($meta['reason'] ?? '') : '',
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
                        'ip_limit' => $ipLimits["{$svc}_{$user}"] ?? 1,
                        'quota' => $quotas["{$svc}_{$user}"] ?? 0
                    ];
                }

                // Add suspended users who are missing from config.json
                foreach (array_keys($suspendedSvc) as $user) {
                    if (empty($user)) continue;
                    if (isset($seen[$user])) continue;
                    $seen[$user] = true;

                    $k = "{$svc}_{$user}";
                    $dbInfo = $dbMap[$k] ?? [];
                    $meta = $suspendedMeta[$k] ?? [];
                    $suspExp = trim((string) ($meta['exp'] ?? ''));
                    if ($suspExp === '') {
                        $resExp = $this->executeBash("awk '{print \$1}' /etc/kyt/suspended/{$svc}/{$user} 2>/dev/null");
                        $suspExp = trim($resExp['output']);
                    }

                    $accounts[] = [
                        'service' => $svc,
                        'username' => $user,
                        'active' => 0, // They are suspended
                        'created_at' => $dbInfo['created_at'] ?? '',
                        'expires_at' => $suspExp ?: ($dbInfo['expires_at'] ?? ''),
                        'ip_limit' => $ipLimits["{$svc}_{$user}"] ?? 1,
                        'quota' => $quotas["{$svc}_{$user}"] ?? 0,
                        'suspend_reason' => (string) ($meta['reason'] ?? ''),
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

    public function updateAccountExpiry($service, $username, $expiresAt)
    {
        $serviceJson = json_encode($service, JSON_UNESCAPED_SLASHES);
        $userJson = json_encode($username, JSON_UNESCAPED_SLASHES);
        $expJson = json_encode($expiresAt, JSON_UNESCAPED_SLASHES);

        $script = <<<PYTHON
import sqlite3, json
service = json.loads('{$serviceJson}')
username = json.loads('{$userJson}')
expires_at = json.loads('{$expJson}')
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.execute(
        "UPDATE account_registry SET expires_at = ?, updated_at = datetime('now','localtime') WHERE service = ? AND username = ? AND active = 1",
        (str(expires_at).strip(), str(service).strip(), str(username).strip())
    )
    c.commit()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
PYTHON;
        $res = $this->runPython($script);
        if (strpos($res['output'], 'ERROR:') !== false) {
            \Illuminate\Support\Facades\Log::error("Failed to update account expiry: " . $res['output']);
        }
        return $res;
    }

    public function renewSshAccount($username, $days, $limitIp)
    {
        $safeUser = escapeshellarg($username);
        $days = (int) $days;
        $limitIp = (int) $limitIp;

        $script = <<<BASH
exp_raw=\$(chage -l {$safeUser} | awk -F": " '/Account expires/ {print \$2}')
if [ -z "\$exp_raw" ] || [ "\$exp_raw" = "never" ] || [ "\$exp_raw" = "Never" ]; then
    base_ts=\$(date +%s)
else
    base_ts=\$(date -d "\$exp_raw" +%s 2>/dev/null || date +%s)
fi
now_ts=\$(date +%s)
if [ "\$base_ts" -lt "\$now_ts" ]; then
    base_ts=\$now_ts
fi
target_ts=\$((base_ts + {$days}*86400))
new_exp=\$(date -u -d "@\${target_ts}" +%Y-%m-%d)
passwd -u {$safeUser} >/dev/null 2>&1 || usermod -U {$safeUser} >/dev/null 2>&1 || true
rm -f /etc/kyt/suspended/ssh/{$username} /etc/kyt/limit/.state/ssh/{$username}.state
usermod -e "\$new_exp" {$safeUser}
if [ {$limitIp} -gt 0 ]; then
  mkdir -p /etc/kyt/limit/ssh/ip
  echo "{$limitIp}" > /etc/kyt/limit/ssh/ip/{$username}
else
  rm -f /etc/kyt/limit/ssh/ip/{$username}
fi
echo "\$new_exp"
BASH;

        $res = $this->executeBash($script);
        $newExp = trim($res['output'] ?? '');
        if (!$res['success'] || $newExp === '') {
            return ['success' => false, 'error' => $res['error'] ?? 'Renew SSH failed'];
        }

        return ['success' => true, 'expires_at' => $newExp];
    }

    public function reduceSshAccount($username, $days, $limitIp)
    {
        $safeUser = escapeshellarg($username);
        $days = (int) $days;
        $limitIp = (int) $limitIp;

        $script = <<<BASH
exp_raw=\$(chage -l {$safeUser} | awk -F": " '/Account expires/ {print \$2}')
if [ -z "\$exp_raw" ] || [ "\$exp_raw" = "never" ] || [ "\$exp_raw" = "Never" ]; then
    base_ts=\$(date +%s)
else
    base_ts=\$(date -d "\$exp_raw" +%s 2>/dev/null || date +%s)
fi
now_ts=\$(date +%s)
target_ts=\$((base_ts - {$days}*86400))
if [ "\$target_ts" -lt "\$now_ts" ]; then
    target_ts=\$now_ts
fi
new_exp=\$(date -u -d "@\${target_ts}" +%Y-%m-%d)
usermod -e "\$new_exp" {$safeUser}
if [ {$limitIp} -gt 0 ]; then
  mkdir -p /etc/kyt/limit/ssh/ip
  echo "{$limitIp}" > /etc/kyt/limit/ssh/ip/{$username}
fi
echo "\$new_exp"
BASH;

        $res = $this->executeBash($script);
        $newExp = trim($res['output'] ?? '');
        if (!$res['success'] || $newExp === '') {
            return ['success' => false, 'error' => $res['error'] ?? 'Reduce SSH duration failed'];
        }

        return ['success' => true, 'expires_at' => $newExp];
    }

    public function reduceXrayAccount($service, $username, $days, $quota, $limitIp)
    {
        $markerMap = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
        $marker = $markerMap[$service] ?? '###';

        $serviceJson = json_encode($service, JSON_UNESCAPED_SLASHES);
        $userJson = json_encode($username, JSON_UNESCAPED_SLASHES);
        $markerJson = json_encode($marker, JSON_UNESCAPED_SLASHES);

        $days = (int) $days;
        $quota = (int) $quota;
        $limitIp = (int) $limitIp;

        $script = <<<PYTHON
import datetime as DT
import json
import os

service = json.loads('{$serviceJson}')
username = json.loads('{$userJson}')
marker = json.loads('{$markerJson}')
sub_days = int({$days})
quota = int({$quota})
limit_ip = int({$limitIp})
path = '/etc/xray/config.json'

def parse_date(text):
    try:
        return DT.date.fromisoformat(text.strip())
    except Exception:
        return None

try:
    with open(path, 'r') as f:
        lines = f.readlines()
except Exception:
    print('ERROR: config not readable')
    raise SystemExit(1)

current_exp = None
for i, line in enumerate(lines):
    parts = line.strip().split()
    if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
        current_exp = parse_date(parts[2])
        break

if not current_exp:
    print('ERROR: user not found')
    raise SystemExit(1)

today = DT.date.today()
new_expiry = current_exp - DT.timedelta(days=sub_days)
if new_expiry < today:
    new_expiry = today

for i, line in enumerate(lines):
    parts = line.strip().split()
    if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
        lines[i] = f"{marker} {username} {new_expiry.isoformat()}\\n"

try:
    with open(path, 'w') as f:
        f.writelines(lines)
except Exception:
    print('ERROR: config not writable')
    raise SystemExit(1)

if limit_ip > 0:
    os.makedirs(f"/etc/kyt/limit/{service}/ip", exist_ok=True)
    with open(f"/etc/kyt/limit/{service}/ip/{username}", "w") as fh:
        fh.write(str(limit_ip))
    try:
        os.remove(f"/etc/kyt/limit/.state/{service}/{username}.state")
    except Exception:
        pass

if service != "shadowsocks":
    quota_path = f"/etc/{service}/{username}"
    if quota > 0:
        os.makedirs(f"/etc/{service}", exist_ok=True)
        with open(quota_path, "w") as fq:
            fq.write(str(quota * 1024 * 1024 * 1024))
    else:
        try:
            os.remove(quota_path)
        except Exception:
            pass

os.system("systemctl restart xray >/dev/null 2>&1")
print(new_expiry.isoformat())
PYTHON;

        $res = $this->runPython($script);
        $newExp = trim($res['output'] ?? '');
        if (!$res['success'] || $newExp === '' || str_starts_with($newExp, 'ERROR:')) {
            return ['success' => false, 'error' => $res['error'] ?? $res['output'] ?? 'Reduce Xray failed'];
        }

        return ['success' => true, 'expires_at' => $newExp];
    }

    public function renewXrayAccount($service, $username, $days, $quota, $limitIp)
    {
        $markerMap = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
        $marker = $markerMap[$service] ?? '###';

        $serviceJson = json_encode($service, JSON_UNESCAPED_SLASHES);
        $userJson = json_encode($username, JSON_UNESCAPED_SLASHES);
        $markerJson = json_encode($marker, JSON_UNESCAPED_SLASHES);

        $days = (int) $days;
        $quota = (int) $quota;
        $limitIp = (int) $limitIp;

        $script = <<<PYTHON
import datetime as DT
import json
import os

service = json.loads('{$serviceJson}')
username = json.loads('{$userJson}')
marker = json.loads('{$markerJson}')
add_days = int({$days})
quota = int({$quota})
limit_ip = int({$limitIp})
path = '/etc/xray/config.json'

def parse_date(text):
    try:
        return DT.date.fromisoformat(text.strip())
    except Exception:
        return None

if os.path.exists(f"/etc/kyt/suspended/{service}/{username}"):
    script_map = {'vmess': 'unsuspws', 'vless': 'unsuspvless', 'trojan': 'unsusptr', 'shadowsocks': 'unsuspss'}
    cmd = script_map.get(service, 'unsuspws')
    os.system(f"{cmd} --user {username} >/dev/null 2>&1")

try:
    with open(path, 'r') as f:
        lines = f.readlines()
except Exception:
    print('ERROR: config not readable')
    raise SystemExit(1)

current_exp = None
for i, line in enumerate(lines):
    parts = line.strip().split()
    if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
        current_exp = parse_date(parts[2])
        break

if not current_exp:
    print('ERROR: user not found')
    raise SystemExit(1)

today = DT.date.today()
base_expiry = current_exp if current_exp >= today else today
new_expiry = base_expiry + DT.timedelta(days=add_days)

for i, line in enumerate(lines):
    parts = line.strip().split()
    if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
        lines[i] = f"{marker} {username} {new_expiry.isoformat()}\\n"

try:
    with open(path, 'w') as f:
        f.writelines(lines)
except Exception:
    print('ERROR: config not writable')
    raise SystemExit(1)

if limit_ip > 0:
    os.makedirs(f"/etc/kyt/limit/{service}/ip", exist_ok=True)
    with open(f"/etc/kyt/limit/{service}/ip/{username}", "w") as fh:
        fh.write(str(limit_ip))
else:
    try:
        os.remove(f"/etc/kyt/limit/{service}/ip/{username}")
    except Exception:
        pass

if service != "shadowsocks":
    quota_path = f"/etc/{service}/{username}"
    try:
        os.remove(quota_path)
    except Exception:
        pass
    if quota > 0:
        with open(quota_path, "w") as fh:
            fh.write(str(quota * 1024 * 1024 * 1024))

db_path = f"/etc/{service}/.{service}.db"
if os.path.exists(db_path):
    try:
        with open(db_path, 'r') as f:
            db_lines = f.readlines()
        for i, line in enumerate(db_lines):
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
                db_lines[i] = f"{marker} {username} {new_expiry.isoformat()}\\n"
        with open(db_path, 'w') as f:
            f.writelines(db_lines)
    except Exception:
        pass

os.system("systemctl restart xray >/dev/null 2>&1")
try:
    os.remove(f"/etc/kyt/limit/.state/{service}/{username}.state")
except Exception:
    pass
print(new_expiry.isoformat())
PYTHON;

        $res = $this->runPython($script);
        $newExp = trim($res['output'] ?? '');
        if (!$res['success'] || $newExp === '' || strpos($newExp, 'ERROR:') === 0) {
            return ['success' => false, 'error' => $res['error'] ?? $res['output'] ?? 'Renew Xray failed'];
        }

        return ['success' => true, 'expires_at' => $newExp];
    }

    public function updateSshAccount(
        string $username,
        string $expiryMode = 'keep',
        int $days = 0,
        ?string $targetDate = null,
        ?int $limitIp = null,
        ?string $password = null,
        bool $reactivate = false
    ): array {
        $payloadB64 = base64_encode(json_encode([
            'username' => $username,
            'expiry_mode' => $expiryMode,
            'days' => max(0, min(365, $days)),
            'target_date' => $targetDate,
            'limit_ip' => $limitIp,
            'password' => $password,
            'reactivate' => $reactivate,
        ]));

        $script = <<<PYTHON
import base64, datetime as DT, json, os, subprocess

cfg = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
username = cfg["username"]
mode = cfg["expiry_mode"]
days = int(cfg["days"] or 0)
target_date = cfg["target_date"]
limit_ip = cfg["limit_ip"]
password = cfg["password"]
reactivate = bool(cfg["reactivate"])

if subprocess.run(["id", "-u", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
    print("ERROR: user not found")
    raise SystemExit(1)

current_exp = None
try:
    out = subprocess.check_output(["chage", "-l", username], text=True, stderr=subprocess.DEVNULL)
    for line in out.splitlines():
        if "Account expires" in line:
            raw = line.split(":", 1)[1].strip()
            if raw and raw.lower() != "never":
                dt_str = subprocess.check_output(["date", "-d", raw, "+%Y-%m-%d"], text=True, stderr=subprocess.DEVNULL).strip()
                current_exp = DT.date.fromisoformat(dt_str)
            break
except Exception:
    pass

today = DT.date.today()
base_exp = current_exp if current_exp is not None else today
new_exp = base_exp

if mode == "add" and days > 0:
    anchor = base_exp if base_exp >= today else today
    new_exp = anchor + DT.timedelta(days=days)
elif mode == "reduce" and days > 0:
    new_exp = base_exp - DT.timedelta(days=days)
    if new_exp < today:
        new_exp = today
elif mode == "set_date" and target_date:
    try:
        new_exp = DT.date.fromisoformat(str(target_date).strip())
    except Exception:
        print("ERROR: invalid target_date")
        raise SystemExit(1)

if mode != "keep":
    subprocess.run(["usermod", "-e", new_exp.isoformat(), username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

if password is not None and str(password) != "":
    p = subprocess.run(["chpasswd"], input=f"{username}:{password}\\n", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        print("ERROR: failed to change ssh password")
        raise SystemExit(1)

if limit_ip is not None and int(limit_ip) > 0:
    os.makedirs("/etc/kyt/limit/ssh/ip", exist_ok=True)
    with open(f"/etc/kyt/limit/ssh/ip/{username}", "w", encoding="utf-8") as fh:
        fh.write(str(int(limit_ip)))
    try:
        os.remove(f"/etc/kyt/limit/.state/ssh/{username}.state")
    except Exception:
        pass

susp_file = f"/etc/kyt/suspended/ssh/{username}"
if reactivate:
    subprocess.run(["passwd", "-u", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    subprocess.run(["usermod", "-U", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    try:
        os.remove(susp_file)
    except Exception:
        pass
    try:
        os.remove(f"/etc/kyt/limit/.state/ssh/{username}.state")
    except Exception:
        pass
elif os.path.isfile(susp_file) and mode != "keep":
    try:
        parts = open(susp_file, "r", encoding="utf-8", errors="ignore").read().strip().split(None, 2)
        lock_tok = parts[1] if len(parts) >= 2 else "locked"
        reason_tok = parts[2] if len(parts) >= 3 else "manual"
        with open(susp_file, "w", encoding="utf-8") as sf:
            sf.write(f"{new_exp.isoformat()} {lock_tok} {reason_tok}\\n")
    except Exception:
        pass

is_still_suspended = os.path.isfile(susp_file)
print(json.dumps({
    "expires_at": new_exp.isoformat(),
    "status": "suspended" if is_still_suspended else "active",
}))
PYTHON;

        $res = $this->runPython($script);
        $rawOut = trim((string) ($res['output'] ?? ''));
        if (!$res['success'] || $rawOut === '' || str_starts_with($rawOut, 'ERROR:')) {
            return ['success' => false, 'error' => $res['error'] ?? $rawOut ?: 'Update SSH failed'];
        }
        $decoded = json_decode($rawOut, true);
        if (!is_array($decoded) || empty($decoded['expires_at'])) {
            return ['success' => false, 'error' => 'Invalid SSH update response: ' . $rawOut];
        }

        return [
            'success' => true,
            'expires_at' => (string) $decoded['expires_at'],
            'status' => (string) ($decoded['status'] ?? 'active'),
        ];
    }

    public function updateXrayAccount(
        string $service,
        string $username,
        string $expiryMode = 'keep',
        int $days = 0,
        ?string $targetDate = null,
        ?int $quota = null,
        ?int $limitIp = null,
        bool $reactivate = false
    ): array {
        $markerMap = ['vmess' => '###', 'vless' => '#&', 'trojan' => '#!', 'shadowsocks' => '#!#'];
        $marker = $markerMap[$service] ?? '###';

        $payloadB64 = base64_encode(json_encode([
            'service' => $service,
            'username' => $username,
            'marker' => $marker,
            'expiry_mode' => $expiryMode,
            'days' => max(0, min(365, $days)),
            'target_date' => $targetDate,
            'quota' => $quota,
            'limit_ip' => $limitIp,
            'reactivate' => $reactivate,
        ]));

        $script = <<<PYTHON
import base64, datetime as DT, json, os, subprocess

cfg = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
service = cfg["service"]
username = cfg["username"]
marker = cfg["marker"]
mode = cfg["expiry_mode"]
days = int(cfg["days"] or 0)
target_date = cfg["target_date"]
quota = cfg["quota"]
limit_ip = cfg["limit_ip"]
reactivate = bool(cfg["reactivate"])

config_path = "/etc/xray/config.json"
susp_path = f"/etc/kyt/suspended/{service}/{username}"
need_restart = False

def parse_date(text):
    try:
        return DT.date.fromisoformat(str(text).strip())
    except Exception:
        return None

if reactivate and os.path.isfile(susp_path):
    script_map = {"vmess": "unsuspws", "vless": "unsuspvless", "trojan": "unsusptr", "shadowsocks": "unsuspss"}
    cmd = script_map.get(service, "unsuspws")
    subprocess.run([cmd, "--user", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    need_restart = True

lines = []
found_in_config = False
current_exp = None

if os.path.isfile(config_path):
    try:
        with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
                found_in_config = True
                current_exp = parse_date(parts[2])
                break
    except Exception:
        pass

found_in_susp = os.path.isfile(susp_path)
if not found_in_config and found_in_susp:
    try:
        parts = open(susp_path, "r", encoding="utf-8", errors="ignore").read().strip().split()
        if parts:
            current_exp = parse_date(parts[0])
    except Exception:
        pass

if not found_in_config and not found_in_susp:
    print("ERROR: user not found")
    raise SystemExit(1)

today = DT.date.today()
base_exp = current_exp if current_exp is not None else today
new_exp = base_exp

if mode == "add" and days > 0:
    anchor = base_exp if base_exp >= today else today
    new_exp = anchor + DT.timedelta(days=days)
elif mode == "reduce" and days > 0:
    new_exp = base_exp - DT.timedelta(days=days)
    if new_exp < today:
        new_exp = today
elif mode == "set_date" and target_date:
    parsed_target = parse_date(target_date)
    if parsed_target is None:
        print("ERROR: invalid target_date")
        raise SystemExit(1)
    new_exp = parsed_target

if mode != "keep":
    if found_in_config:
        for i, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0] == marker and parts[1].lower() == username.lower():
                lines[i] = f"{marker} {username} {new_exp.isoformat()}\\n"
        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        need_restart = True

    if found_in_susp and os.path.isfile(susp_path):
        try:
            parts = open(susp_path, "r", encoding="utf-8", errors="ignore").read().strip().split(None, 2)
            uuid_tok = parts[1] if len(parts) >= 2 else ""
            reason_tok = parts[2] if len(parts) >= 3 else "manual"
            if uuid_tok:
                with open(susp_path, "w", encoding="utf-8") as sf:
                    sf.write(f"{new_exp.isoformat()} {uuid_tok} {reason_tok}\\n")
        except Exception:
            pass

    db_path = f"/etc/{service}/.{service}.db"
    if os.path.isfile(db_path):
        try:
            with open(db_path, "r", encoding="utf-8", errors="ignore") as f:
                db_lines = f.readlines()
            for i, line in enumerate(db_lines):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1].lower() == username.lower():
                    rest = " ".join(parts[3:])
                    db_lines[i] = f"{parts[0]} {username} {new_exp.isoformat()}" + (f" {rest}" if rest else "") + "\\n"
            with open(db_path, "w", encoding="utf-8") as f:
                f.writelines(db_lines)
        except Exception:
            pass

if limit_ip is not None:
    ip_val = int(limit_ip)
    os.makedirs(f"/etc/kyt/limit/{service}/ip", exist_ok=True)
    if ip_val > 0:
        with open(f"/etc/kyt/limit/{service}/ip/{username}", "w", encoding="utf-8") as fh:
            fh.write(str(ip_val))
    try:
        os.remove(f"/etc/kyt/limit/.state/{service}/{username}.state")
    except Exception:
        pass

if quota is not None and service != "shadowsocks":
    q_val = int(quota)
    quota_path = f"/etc/{service}/{username}"
    if q_val > 0:
        os.makedirs(f"/etc/{service}", exist_ok=True)
        with open(quota_path, "w", encoding="utf-8") as fq:
            fq.write(str(q_val * 1024 * 1024 * 1024))
    else:
        try:
            os.remove(quota_path)
        except Exception:
            pass

if reactivate:
    try:
        os.remove(f"/etc/kyt/limit/.state/{service}/{username}.state")
    except Exception:
        pass

if need_restart:
    subprocess.run(["systemctl", "restart", "xray"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

is_still_suspended = os.path.isfile(susp_path) and not found_in_config
print(json.dumps({
    "expires_at": new_exp.isoformat(),
    "status": "suspended" if is_still_suspended else "active",
}))
PYTHON;

        $res = $this->runPython($script);
        $rawOut = trim((string) ($res['output'] ?? ''));
        if (!$res['success'] || $rawOut === '' || str_starts_with($rawOut, 'ERROR:')) {
            return ['success' => false, 'error' => $res['error'] ?? $rawOut ?: 'Update Xray failed'];
        }
        $decoded = json_decode($rawOut, true);
        if (!is_array($decoded) || empty($decoded['expires_at'])) {
            return ['success' => false, 'error' => 'Invalid Xray update response: ' . $rawOut];
        }

        return [
            'success' => true,
            'expires_at' => (string) $decoded['expires_at'],
            'status' => (string) ($decoded['status'] ?? 'active'),
        ];
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
