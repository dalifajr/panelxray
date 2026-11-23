<?php

namespace App\Services;

use App\Models\User;
use App\Models\VpnAccount;
use Illuminate\Support\Facades\Log;
use InvalidArgumentException;

class VpnAccountManager
{
    public const PROTOCOLS = ['ssh', 'vmess', 'vless', 'trojan', 'shadowsocks'];
    public const USERNAME_REGEX = '/^[a-zA-Z0-9_-]{3,24}$/';

    private const XRAY_MARKERS = [
        'vmess' => '###',
        'vless' => '#&',
        'trojan' => '#!',
        'shadowsocks' => '#!#',
    ];

    private const ADD_SCRIPTS = [
        'vmess' => 'addws',
        'vless' => 'addvless',
        'trojan' => 'addtr',
        'shadowsocks' => 'addss',
    ];

    private const SUSP_SCRIPTS = [
        'vmess' => 'suspws',
        'vless' => 'suspvless',
        'trojan' => 'susptr',
        'shadowsocks' => 'suspss',
    ];

    private const UNSUSP_SCRIPTS = [
        'vmess' => 'unsuspws',
        'vless' => 'unsuspvless',
        'trojan' => 'unsusptr',
        'shadowsocks' => 'unsuspss',
    ];

    public function __construct(
        protected VpnService $vpn
    ) {}

    public function assertProtocol(string $protocol): string
    {
        $normalized = strtolower(trim($protocol));
        if (!in_array($normalized, self::PROTOCOLS, true)) {
            throw new InvalidArgumentException("Unsupported VPN protocol: {$protocol}");
        }
        return $normalized;
    }

    public function assertUsername(string $username): string
    {
        $trimmed = trim($username);
        if (!preg_match(self::USERNAME_REGEX, $trimmed)) {
            throw new InvalidArgumentException('Username must be 3-24 characters using only letters, numbers, underscores, or hyphens.');
        }
        return $trimmed;
    }

    public function health(): array
    {
        $ping = $this->vpn->executeBash('echo BRIDGE_OK');
        $bridgeOk = !empty($ping['success']) && str_contains((string) ($ping['output'] ?? ''), 'BRIDGE_OK');

        $domain = '';
        $xrayActive = false;
        $sshActive = false;
        $counts = [];

        if ($bridgeOk) {
            $infoRes = $this->vpn->executeBash(
                'DOMAIN=$(cat /etc/xray/domain 2>/dev/null | head -n 1); '
                . 'XRAY=$(systemctl is-active xray 2>/dev/null || echo inactive); '
                . 'SSH=$(systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || echo inactive); '
                . 'echo "DOMAIN=${DOMAIN}"; echo "XRAY=${XRAY}"; echo "SSH=${SSH}"'
            );

            foreach (explode("\n", (string) ($infoRes['output'] ?? '')) as $line) {
                $line = trim($line);
                if (str_starts_with($line, 'DOMAIN=')) {
                    $domain = trim(substr($line, 7));
                } elseif (str_starts_with($line, 'XRAY=')) {
                    $xrayActive = trim(substr($line, 5)) === 'active';
                } elseif (str_starts_with($line, 'SSH=')) {
                    $sshActive = trim(substr($line, 4)) === 'active';
                }
            }

            $all = $this->vpn->getAccounts(null);
            foreach (self::PROTOCOLS as $proto) {
                $counts[$proto] = 0;
            }
            foreach ($all as $acc) {
                $svc = strtolower((string) ($acc['service'] ?? ''));
                if (isset($counts[$svc])) {
                    $counts[$svc]++;
                }
            }
        }

        return [
            'bridge_ok' => $bridgeOk,
            'xray_active' => $xrayActive,
            'ssh_active' => $sshActive,
            'domain' => $domain,
            'server_time' => now()->toIso8601String(),
            'account_counts' => $counts,
            'total_accounts' => array_sum($counts),
        ];
    }

    public function checkUsername(string $username, ?string $protocol = null): array
    {
        $username = $this->assertUsername($username);
        if ($protocol !== null && $protocol !== '' && $protocol !== 'all') {
            $protocol = $this->assertProtocol($protocol);
        } else {
            $protocol = null;
        }

        // Always enforce global username uniqueness across ALL protocols (SQLite + all Xray markers + Linux SSH)
        $payloadB64 = base64_encode(json_encode([
            'username' => $username,
        ]));

        $py = <<<PYTHON
import base64, json, sqlite3

data = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
username = data["username"]

in_db = False
try:
    conn = sqlite3.connect('/usr/bin/kyt/database.db')
    row = conn.execute("SELECT COUNT(*) FROM account_registry WHERE LOWER(username)=LOWER(?)", (username,)).fetchone()
    in_db = bool(row and row[0] > 0)
except Exception:
    in_db = False

in_xray = False
markers = ['###', '#&', '#!', '#!#']
try:
    with open('/etc/xray/config.json', 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] in markers and parts[1].lower() == username.lower():
                in_xray = True
                break
except Exception:
    in_xray = False

print(json.dumps({"in_db": in_db, "in_xray": in_xray}))
PYTHON;

        $pyRes = $this->vpn->runPython($py);
        $parsed = json_decode((string) ($pyRes['output'] ?? ''), true) ?? [];
        $inDb = (bool) ($parsed['in_db'] ?? false);
        $inXray = (bool) ($parsed['in_xray'] ?? false);

        $safeUser = escapeshellarg($username);
        $sshRes = $this->vpn->executeBash("id -u {$safeUser} >/dev/null 2>&1 && echo 1 || echo 0");
        $lines = explode("\n", trim((string) ($sshRes['output'] ?? '0')));
        $inSsh = ((int) end($lines)) === 1;

        $exists = $inDb || $inXray || $inSsh;

        return [
            'username' => $username,
            'protocol' => $protocol ?? 'all',
            'exists' => $exists,
            'available' => !$exists,
        ];
    }

    public function listAccounts(?string $protocol = null, ?string $status = null, ?string $search = null, bool $includeConfig = false): array
    {
        $protoFilter = null;
        if ($protocol !== null && $protocol !== '' && strtolower($protocol) !== 'all') {
            $protoFilter = $this->assertProtocol($protocol);
        }

        $raw = $this->vpn->getAccounts($protoFilter);

        $localMap = VpnAccount::query()
            ->when($protoFilter, fn ($q) => $q->where('service', $protoFilter))
            ->get()
            ->keyBy(fn ($a) => strtolower($a->service . ':' . $a->vpn_username));

        $bulkConfigs = $includeConfig ? $this->readAllXrayConfigsBulk() : ['domain' => '', 'uuids' => []];
        $bulkDomain = (string) ($bulkConfigs['domain'] ?? '');
        $bulkUuids = is_array($bulkConfigs['uuids'] ?? null) ? $bulkConfigs['uuids'] : [];

        $items = [];
        $searchLower = $search !== null ? strtolower(trim($search)) : '';
        $statusLower = $status !== null ? strtolower(trim($status)) : 'all';

        foreach ($raw as $row) {
            $svc = strtolower((string) ($row['service'] ?? ''));
            $uname = (string) ($row['username'] ?? '');
            if ($svc === '' || $uname === '') {
                continue;
            }

            if ($searchLower !== '' && !str_contains(strtolower($uname), $searchLower)) {
                continue;
            }

            $activeFlag = (int) ($row['active'] ?? 1);
            $expiresAt = (string) ($row['expires_at'] ?? '');
            $computedStatus = 'active';
            if ($activeFlag === 0) {
                $computedStatus = 'suspended';
            } elseif ($expiresAt !== '' && strtotime($expiresAt) !== false && strtotime($expiresAt . ' 23:59:59') < time()) {
                $computedStatus = 'expired';
            }

            if ($statusLower !== '' && $statusLower !== 'all' && $computedStatus !== $statusLower) {
                continue;
            }

            $local = $localMap->get(strtolower($svc . ':' . $uname));
            $quotaGb = (int) ($row['quota'] ?? 0);
            $ipLimit = max(1, (int) ($row['ip_limit'] ?? 1));

            $entry = [
                'protocol' => $svc,
                'username' => $uname,
                'status' => $computedStatus,
                'active' => $activeFlag === 1,
                'admin_suspended' => (bool) ($local?->admin_suspended ?? false),
                'is_trial' => (bool) ($local?->is_trial ?? false),
                'created_at' => (string) ($row['created_at'] ?? ''),
                'expired_at' => $expiresAt,
                'quota_gb' => $quotaGb,
                'ip_limit' => $ipLimit,
            ];

            if ($includeConfig) {
                if ($svc === 'ssh') {
                    $sshInfo = [
                        'host' => $bulkDomain,
                        'username' => $uname,
                        'password' => null,
                        'ports' => [
                            'openssh' => 22,
                            'ws_tls' => 443,
                            'ws_ntls' => 80,
                            'dropbear' => '109, 143',
                            'udp_custom' => '1-65535',
                        ],
                        'ws_payload' => "GET / HTTP/1.1[crlf]Host: {$bulkDomain}[crlf]Upgrade: websocket[crlf][crlf]",
                    ];
                    $entry['domain'] = $bulkDomain;
                    $entry['uuid'] = null;
                    $entry['ports'] = $sshInfo['ports'];
                    $entry['links'] = [];
                    $entry['ssh_info'] = $sshInfo;
                    $entry['formatted_text'] = $this->formatSshText($sshInfo, $expiresAt, $ipLimit);
                } else {
                    $uuid = (string) ($bulkUuids[strtolower($svc . ':' . $uname)] ?? '');
                    $links = $this->buildXrayLinks($svc, $bulkDomain, $uuid, $uname, '3');
                    $entry['domain'] = $bulkDomain;
                    $entry['uuid'] = $uuid !== '' ? $uuid : null;
                    $entry['ports'] = ['tls' => 443, 'ntls' => 80, 'grpc' => 443];
                    $entry['links'] = $links;
                    $entry['ssh_info'] = null;
                    $entry['formatted_text'] = $this->formatXrayText($svc, $uname, $bulkDomain, $uuid, $quotaGb, $ipLimit, $expiresAt, $links);
                }
            }

            $items[] = $entry;
        }

        return $items;
    }

    private function readAllXrayConfigsBulk(): array
    {
        $py = <<<'PYTHON'
import json, os, re, glob

domain = ''
try:
    with open('/etc/xray/domain', 'r', encoding='utf-8') as f:
        domain = f.read().strip()
except Exception:
    pass

marker_to_svc = {'###': 'vmess', '#&': 'vless', '#!': 'trojan', '#!#': 'shadowsocks'}
uuids = {}

try:
    with open('/etc/xray/config.json', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] in marker_to_svc:
            svc = marker_to_svc[parts[0]]
            uname = parts[1].lower()
            key = f"{svc}:{uname}"
            if key not in uuids and i + 1 < len(lines):
                m = re.search(r'"(id|password)"\s*:\s*"([^"]+)"', lines[i + 1])
                if m:
                    uuids[key] = m.group(2)
except Exception:
    pass

for svc in ('vmess', 'vless', 'trojan', 'shadowsocks'):
    for sp in glob.glob(f'/etc/kyt/suspended/{svc}/*'):
        uname = os.path.basename(sp).lower()
        key = f"{svc}:{uname}"
        if key not in uuids:
            try:
                with open(sp, 'r', encoding='utf-8', errors='ignore') as f:
                    m = re.search(r'"(id|password)"\s*:\s*"([^"]+)"', f.read())
                    if m:
                        uuids[key] = m.group(2)
            except Exception:
                pass

print(json.dumps({'domain': domain, 'uuids': uuids}))
PYTHON;

        $res = $this->vpn->runPython($py);
        if (!empty($res['success'])) {
            $decoded = json_decode((string) ($res['output'] ?? ''), true);
            if (is_array($decoded)) {
                return $decoded;
            }
        }
        return ['domain' => '', 'uuids' => []];
    }

    public function getAccountDetail(string $protocol, string $username, string $sniMode = '3', ?string $plainPassword = null): ?array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $sniMode = in_array($sniMode, ['1', '2', '3'], true) ? $sniMode : '3';

        $accounts = $this->listAccounts($protocol, 'all', $username);
        $matched = null;
        foreach ($accounts as $acc) {
            if (strtolower($acc['username']) === strtolower($username)) {
                $matched = $acc;
                break;
            }
        }

        if ($protocol === 'ssh') {
            $domainRes = $this->vpn->executeBash('cat /etc/xray/domain 2>/dev/null | head -n 1');
            $domain = trim((string) ($domainRes['output'] ?? ''));

            if (!$matched) {
                $safeUser = escapeshellarg($username);
                $existsRes = $this->vpn->executeBash("id -u {$safeUser} >/dev/null 2>&1 && echo 1 || echo 0");
                if (trim((string) ($existsRes['output'] ?? '0')) !== '1') {
                    return null;
                }
            }

            $expiredAt = $matched['expired_at'] ?? '';
            $ipLimit = (int) ($matched['ip_limit'] ?? 1);
            $status = $matched['status'] ?? 'active';

            $sshInfo = [
                'host' => $domain,
                'username' => $username,
                'password' => $plainPassword,
                'ports' => [
                    'openssh' => 22,
                    'ws_tls' => 443,
                    'ws_ntls' => 80,
                    'dropbear' => '109, 143',
                    'udp_custom' => '1-65535',
                ],
                'ws_payload' => "GET / HTTP/1.1[crlf]Host: {$domain}[crlf]Upgrade: websocket[crlf][crlf]",
            ];

            return [
                'protocol' => 'ssh',
                'username' => $username,
                'domain' => $domain,
                'uuid' => null,
                'password' => $plainPassword,
                'status' => $status,
                'quota_gb' => 0,
                'ip_limit' => $ipLimit,
                'expired_at' => $expiredAt,
                'ports' => $sshInfo['ports'],
                'links' => [],
                'ssh_info' => $sshInfo,
                'formatted_text' => $this->formatSshText($sshInfo, $expiredAt, $ipLimit),
            ];
        }

        // Xray protocol config lookup (safe parameterized Python)
        $cfg = $this->readXrayAccountConfigSafe($protocol, $username);
        if (empty($cfg['success']) || (empty($cfg['uuid']) && !$matched)) {
            return null;
        }

        $domain = (string) ($cfg['domain'] ?? '');
        $uuid = (string) ($cfg['uuid'] ?? '');
        $quotaGb = is_numeric($cfg['quota'] ?? null) ? (int) $cfg['quota'] : (int) ($matched['quota_gb'] ?? 0);
        $ipLimit = is_numeric($cfg['ip_limit'] ?? null) ? (int) $cfg['ip_limit'] : (int) ($matched['ip_limit'] ?? 1);
        $expiredAt = (string) ($cfg['expires_at'] ?? ($matched['expired_at'] ?? ''));
        $status = $matched['status'] ?? (!empty($cfg['suspended']) ? 'suspended' : 'active');

        $links = $this->buildXrayLinks($protocol, $domain, $uuid, $username, $sniMode);
        $ports = ['tls' => 443, 'ntls' => 80, 'grpc' => 443];

        return [
            'protocol' => $protocol,
            'username' => $username,
            'domain' => $domain,
            'uuid' => $uuid,
            'password' => null,
            'sni_mode' => $sniMode,
            'status' => $status,
            'quota_gb' => $quotaGb,
            'ip_limit' => $ipLimit,
            'expired_at' => $expiredAt,
            'ports' => $ports,
            'links' => $links,
            'ssh_info' => null,
            'formatted_text' => $this->formatXrayText($protocol, $username, $domain, $uuid, $quotaGb, $ipLimit, $expiredAt, $links),
        ];
    }

    public function createAccount(array $payload): array
    {
        $protocol = $this->assertProtocol((string) ($payload['protocol'] ?? ''));
        $username = $this->assertUsername((string) ($payload['username'] ?? ''));
        $days = max(1, min(365, (int) ($payload['days'] ?? 30)));
        $quotaGb = max(0, min(10000, (int) ($payload['quota_gb'] ?? 0)));
        $ipLimit = max(1, min(50, (int) ($payload['ip_limit'] ?? 1)));
        $sniMode = in_array((string) ($payload['sni_mode'] ?? '3'), ['1', '2', '3'], true)
            ? (string) $payload['sni_mode']
            : '3';
        $password = isset($payload['password']) ? (string) $payload['password'] : '';
        $externalRef = isset($payload['external_ref']) ? substr(trim((string) $payload['external_ref']), 0, 120) : 'store_api';

        if ($protocol === 'ssh') {
            if ($password === '' || preg_match('/[\r\n\0]/', $password) || strlen($password) > 64) {
                throw new InvalidArgumentException('Valid SSH password (1-64 chars, no newlines) is required.');
            }
        }

        $check = $this->checkUsername($username, null);
        if (!empty($check['exists'])) {
            throw new \RuntimeException("Username '{$username}' already exists on this server.", 409);
        }

        $expiryDate = date('Y-m-d', strtotime("+{$days} days"));

        if ($protocol === 'ssh') {
            $safeUser = escapeshellarg($username);
            $safeExp = escapeshellarg($expiryDate);
            $createRes = $this->vpn->executeBash("useradd -e {$safeExp} -s /bin/false -M {$safeUser}");
            if (empty($createRes['success'])) {
                throw new \RuntimeException('Failed to create SSH user: ' . ($createRes['error'] ?? 'Unknown error'), 502);
            }

            $chpasswdRes = $this->vpn->executeBashWithStdin('chpasswd', "{$username}:{$password}\n");
            if (empty($chpasswdRes['success'])) {
                $this->vpn->executeBash("userdel -f {$safeUser} 2>/dev/null || true");
                throw new \RuntimeException('Failed to set SSH password: ' . ($chpasswdRes['error'] ?? 'Unknown error'), 502);
            }

            $limitPath = '/etc/kyt/limit/ssh/ip/' . $username;
            $safeLimitPath = escapeshellarg($limitPath);
            $this->vpn->executeBash("mkdir -p /etc/kyt/limit/ssh/ip && printf '%s\n' " . escapeshellarg((string) $ipLimit) . " > {$safeLimitPath}");
        } else {
            $cmd = self::ADD_SCRIPTS[$protocol];
            $stdin = implode("\n", [$sniMode, $username, $days, $quotaGb, $ipLimit]) . "\n";
            $createRes = $this->vpn->executeBashWithStdin($cmd, $stdin);
            if (empty($createRes['success'])) {
                throw new \RuntimeException("Failed to create {$protocol} account: " . ($createRes['error'] ?? 'Unknown error'), 502);
            }
        }

        $this->upsertSqliteRegistry($externalRef, $protocol, $username, $expiryDate, false);
        $this->syncLocalVpnAccountRecord($protocol, $username, false);

        $detail = $this->getAccountDetail($protocol, $username, $sniMode, $protocol === 'ssh' ? $password : null);
        if (!$detail) {
            return [
                'protocol' => $protocol,
                'username' => $username,
                'domain' => '',
                'uuid' => null,
                'password' => $protocol === 'ssh' ? $password : null,
                'status' => 'active',
                'quota_gb' => $quotaGb,
                'ip_limit' => $ipLimit,
                'expired_at' => $expiryDate,
                'ports' => [],
                'links' => [],
                'ssh_info' => null,
                'formatted_text' => "Protocol: {$protocol}\nUsername: {$username}\nExpired: {$expiryDate}",
            ];
        }

        if (empty($detail['expired_at'])) {
            $detail['expired_at'] = $expiryDate;
        }

        return $detail;
    }

    public function renewAccount(string $protocol, string $username, int $days, ?int $quotaGb = null, ?int $ipLimit = null): array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $days = max(1, min(365, $days));

        $existing = $this->getAccountDetail($protocol, $username);
        if (!$existing) {
            throw new \RuntimeException("Account {$protocol}/{$username} not found.", 404);
        }

        $resolvedQuota = $quotaGb !== null ? max(0, min(10000, $quotaGb)) : (int) ($existing['quota_gb'] ?? 0);
        $resolvedIp = $ipLimit !== null ? max(1, min(50, $ipLimit)) : max(1, (int) ($existing['ip_limit'] ?? 1));

        if ($protocol === 'ssh') {
            $res = $this->vpn->renewSshAccount($username, $days, $resolvedIp);
        } else {
            $res = $this->vpn->renewXrayAccount($protocol, $username, $days, $resolvedQuota, $resolvedIp);
        }

        if (empty($res['success'])) {
            throw new \RuntimeException('Failed to renew account: ' . ($res['error'] ?? 'Unknown error'), 502);
        }

        $newExpiry = (string) ($res['expires_at'] ?? date('Y-m-d', strtotime("+{$days} days")));
        $this->updateSqliteStatusAndExpiry($protocol, $username, 1, $newExpiry);

        VpnAccount::where('service', $protocol)
            ->where('vpn_username', $username)
            ->update(['admin_suspended' => false, 'is_trial' => false]);

        $updated = $this->getAccountDetail($protocol, $username);

        return [
            'protocol' => $protocol,
            'username' => $username,
            'status' => 'active',
            'expired_at' => $newExpiry,
            'quota_gb' => $resolvedQuota,
            'ip_limit' => $resolvedIp,
            'detail' => $updated,
        ];
    }

    public function suspendAccount(string $protocol, string $username, ?string $reason = null, bool $adminSuspended = true): array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $safeUser = escapeshellarg($username);

        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -L {$safeUser}");
        } else {
            $cmd = self::SUSP_SCRIPTS[$protocol];
            $safeReason = escapeshellarg($reason ? substr(preg_replace('/[^a-zA-Z0-9 _.-]/', '', $reason), 0, 60) : 'api_suspend');
            $res = $this->vpn->executeBash("{$cmd} --user {$safeUser} --reason {$safeReason}");
        }

        if (empty($res['success'])) {
            throw new \RuntimeException('Failed to suspend account: ' . ($res['error'] ?? 'Unknown error'), 502);
        }

        $this->updateSqliteStatusAndExpiry($protocol, $username, 0, null);

        VpnAccount::where('service', $protocol)
            ->where('vpn_username', $username)
            ->update(['admin_suspended' => $adminSuspended]);

        return [
            'protocol' => $protocol,
            'username' => $username,
            'status' => 'suspended',
        ];
    }

    public function unsuspendAccount(string $protocol, string $username): array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $safeUser = escapeshellarg($username);

        if ($protocol === 'ssh') {
            $res = $this->vpn->executeBash("usermod -U {$safeUser}");
        } else {
            $cmd = self::UNSUSP_SCRIPTS[$protocol];
            $res = $this->vpn->executeBash("{$cmd} --user {$safeUser}");
        }

        if (empty($res['success'])) {
            throw new \RuntimeException('Failed to unsuspend account: ' . ($res['error'] ?? 'Unknown error'), 502);
        }

        $this->updateSqliteStatusAndExpiry($protocol, $username, 1, null);

        VpnAccount::where('service', $protocol)
            ->where('vpn_username', $username)
            ->update(['admin_suspended' => false]);

        return [
            'protocol' => $protocol,
            'username' => $username,
            'status' => 'active',
        ];
    }

    public function deleteAccount(string $protocol, string $username): array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $safeUser = escapeshellarg($username);

        if ($protocol === 'ssh') {
            $limitFile = escapeshellarg('/etc/kyt/limit/ssh/ip/' . $username);
            $this->vpn->executeBash("userdel -f {$safeUser} 2>/dev/null || true; rm -f {$limitFile}");
        } else {
            $marker = self::XRAY_MARKERS[$protocol];
            $payloadB64 = base64_encode(json_encode([
                'protocol' => $protocol,
                'username' => $username,
                'marker' => $marker,
            ]));

            $py = <<<PYTHON
import base64, json, os, shutil, subprocess

data = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
protocol = data["protocol"]
username = data["username"]
marker = data["marker"]
path = '/etc/xray/config.json'

changed = False
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    next_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            if '},{"' in line or '"password"' in line or '"id"' in line or '"method"' in line:
                changed = True
                skip_next = False
                continue
            skip_next = False
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == marker and parts[1].lower() == username.lower():
            changed = True
            skip_next = True
            continue
        next_lines.append(line)
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(next_lines)
        subprocess.run(['systemctl', 'restart', 'xray'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for p in [
    f'/etc/kyt/suspended/{protocol}/{username}',
    f'/etc/kyt/limit/{protocol}/ip/{username}',
    f'/etc/{protocol}/{username}',
]:
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
    elif os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass

db_file = f'/etc/{protocol}/.{protocol}.db'
if os.path.exists(db_file):
    try:
        with open(db_file, 'r', encoding='utf-8', errors='ignore') as f:
            db_lines = f.readlines()
        kept = []
        for l in db_lines:
            parts = l.strip().split()
            if len(parts) >= 2 and parts[1].lower() == username.lower():
                continue
            kept.append(l)
        with open(db_file, 'w', encoding='utf-8') as f:
            f.writelines(kept)
    except Exception:
        pass

print('SUCCESS')
PYTHON;
            $res = $this->vpn->runPython($py);
            Log::info("ExternalAPI DELETE {$protocol}/{$username} result: " . ($res['output'] ?? ''));
        }

        $this->deleteSqliteRegistry($protocol, $username);

        VpnAccount::where('service', $protocol)
            ->where('vpn_username', $username)
            ->delete();

        return [
            'deleted' => true,
            'protocol' => $protocol,
            'username' => $username,
        ];
    }

    private function readXrayAccountConfigSafe(string $protocol, string $username): array
    {
        $marker = self::XRAY_MARKERS[$protocol] ?? '###';
        $payloadB64 = base64_encode(json_encode([
            'service' => $protocol,
            'username' => $username,
            'marker' => $marker,
        ]));

        $py = <<<PYTHON
import base64, json, os, re

data = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
service = data["service"]
username = data["username"]
marker = data["marker"]

domain = ''
try:
    with open('/etc/xray/domain', 'r', encoding='utf-8') as f:
        domain = f.read().strip()
except Exception:
    pass

uuid = ''
expires_at = ''
suspended = False

try:
    with open('/etc/xray/config.json', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == marker and parts[1].lower() == username.lower():
            if len(parts) >= 3:
                expires_at = parts[2]
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().rstrip(',')
                m = re.search(r'"(id|password)"\s*:\s*"([^"]+)"', next_line)
                if m:
                    uuid = m.group(2)
            break
except Exception:
    pass

susp_path = f'/etc/kyt/suspended/{service}/{username}'
if os.path.exists(susp_path):
    suspended = True
    try:
        with open(susp_path, 'r', encoding='utf-8', errors='ignore') as f:
            txt = f.read().strip()
            parts = txt.split()
            if not expires_at and len(parts) >= 1:
                expires_at = parts[0]
            if not uuid:
                m = re.search(r'"(id|password)"\s*:\s*"([^"]+)"', txt)
                if m:
                    uuid = m.group(2)
    except Exception:
        pass

quota = 0
try:
    with open(f'/etc/{service}/{username}', 'r', encoding='utf-8') as f:
        val = int(f.read().strip())
        quota = val // (1024 * 1024 * 1024)
except Exception:
    quota = 0

ip_limit = 1
try:
    with open(f'/etc/kyt/limit/{service}/ip/{username}', 'r', encoding='utf-8') as f:
        ip_limit = int(f.read().strip())
except Exception:
    ip_limit = 1

print(json.dumps({
    'success': True,
    'domain': domain,
    'uuid': uuid,
    'quota': quota,
    'ip_limit': ip_limit,
    'expires_at': expires_at,
    'suspended': suspended,
    'username': username,
    'service': service,
}))
PYTHON;

        $res = $this->vpn->runPython($py);
        if (!empty($res['success'])) {
            $decoded = json_decode((string) ($res['output'] ?? ''), true);
            if (is_array($decoded)) {
                return $decoded;
            }
        }

        return ['success' => false];
    }

    private function upsertSqliteRegistry(string $ownerTag, string $protocol, string $username, string $expiresAt, bool $isTrial): void
    {
        $category = $protocol === 'ssh' ? 'ssh' : 'xray';
        $payloadB64 = base64_encode(json_encode([
            'tg_id' => $ownerTag,
            'service' => $protocol,
            'category' => $category,
            'username' => $username,
            'is_trial' => $isTrial ? 1 : 0,
            'expires_at' => $expiresAt,
        ]));

        $py = <<<PYTHON
import base64, json, sqlite3
d = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.execute(
        "INSERT OR REPLACE INTO account_registry (tg_id, service, category, username, is_trial, created_at, expires_at, active) "
        "VALUES (?, ?, ?, ?, ?, date('now', 'localtime'), ?, 1)",
        (d['tg_id'], d['service'], d['category'], d['username'], d['is_trial'], d['expires_at'])
    )
    c.commit()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
PYTHON;
        $this->vpn->runPython($py);
    }

    private function updateSqliteStatusAndExpiry(string $protocol, string $username, int $active, ?string $expiresAt): void
    {
        $payloadB64 = base64_encode(json_encode([
            'service' => $protocol,
            'username' => $username,
            'active' => $active,
            'expires_at' => $expiresAt,
        ]));

        $py = <<<PYTHON
import base64, json, sqlite3
d = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    if d['expires_at']:
        c.execute(
            "UPDATE account_registry SET active = ?, expires_at = ?, updated_at = datetime('now','localtime') WHERE LOWER(service)=LOWER(?) AND LOWER(username)=LOWER(?)",
            (d['active'], d['expires_at'], d['service'], d['username'])
        )
    else:
        c.execute(
            "UPDATE account_registry SET active = ?, updated_at = datetime('now','localtime') WHERE LOWER(service)=LOWER(?) AND LOWER(username)=LOWER(?)",
            (d['active'], d['service'], d['username'])
        )
    c.commit()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
PYTHON;
        $this->vpn->runPython($py);
    }

    private function deleteSqliteRegistry(string $protocol, string $username): void
    {
        $payloadB64 = base64_encode(json_encode([
            'service' => $protocol,
            'username' => $username,
        ]));

        $py = <<<PYTHON
import base64, json, sqlite3
d = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
try:
    c = sqlite3.connect('/usr/bin/kyt/database.db')
    c.execute(
        "DELETE FROM account_registry WHERE LOWER(service)=LOWER(?) AND LOWER(username)=LOWER(?)",
        (d['service'], d['username'])
    )
    c.commit()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
PYTHON;
        $this->vpn->runPython($py);
    }

    private function syncLocalVpnAccountRecord(string $protocol, string $username, bool $isTrial): void
    {
        try {
            $adminId = User::where('role', 'admin')->value('id');
            if (!$adminId) {
                return;
            }
            VpnAccount::firstOrCreate(
                ['service' => $protocol, 'vpn_username' => $username],
                ['user_id' => $adminId, 'is_trial' => $isTrial, 'admin_suspended' => false]
            );
        } catch (\Throwable $e) {
            Log::warning('ExternalAPI local VpnAccount sync skipped: ' . $e->getMessage());
        }
    }

    public function buildXrayLinks(string $protocol, string $domain, string $uuid, string $username, string $sniMode = '3'): array
    {
        if ($domain === '' || $uuid === '') {
            return [];
        }

        $addr = $domain;
        $host = $domain;
        $sni = $domain;
        $label = $username;

        if ($sniMode === '1') {
            $addr = 'support.zoom.us';
            $host = 'support.zoom.us.' . $domain;
            $sni = $host;
            $label = $username . ' (Zoom)';
        } elseif ($sniMode === '2') {
            $sni = 'live.iflix.com';
            $label = $username . ' (Iflix)';
        }

        $encodedLabel = rawurlencode($label);

        if ($protocol === 'vmess') {
            $tlsObj = [
                'v' => '2', 'ps' => $label, 'add' => $addr, 'port' => '443',
                'id' => $uuid, 'aid' => '0', 'net' => 'ws', 'path' => '/vmess',
                'type' => 'none', 'host' => $host, 'tls' => 'tls', 'sni' => $sni, 'allowInsecure' => true,
            ];
            $ntlsObj = [
                'v' => '2', 'ps' => $label, 'add' => $addr, 'port' => '80',
                'id' => $uuid, 'aid' => '0', 'net' => 'ws', 'path' => '/vmess',
                'type' => 'none', 'host' => $host, 'tls' => 'none',
            ];
            $grpcObj = [
                'v' => '2', 'ps' => $label . ' gRPC', 'add' => $addr, 'port' => '443',
                'id' => $uuid, 'aid' => '0', 'net' => 'grpc', 'path' => 'vmess-grpc',
                'type' => 'none', 'host' => $host, 'tls' => 'tls', 'sni' => $sni,
            ];

            return [
                'tls' => 'vmess://' . base64_encode(json_encode($tlsObj, JSON_UNESCAPED_SLASHES)),
                'ntls' => 'vmess://' . base64_encode(json_encode($ntlsObj, JSON_UNESCAPED_SLASHES)),
                'grpc' => 'vmess://' . base64_encode(json_encode($grpcObj, JSON_UNESCAPED_SLASHES)),
            ];
        }

        if ($protocol === 'vless') {
            return [
                'tls' => "vless://{$uuid}@{$addr}:443?path=/vless&security=tls&encryption=none&type=ws&host={$host}&sni={$sni}#{$encodedLabel}",
                'ntls' => "vless://{$uuid}@{$addr}:80?path=/vless&encryption=none&type=ws&host={$host}#{$encodedLabel}",
                'grpc' => "vless://{$uuid}@{$addr}:443?mode=gun&security=tls&encryption=none&type=grpc&serviceName=vless-grpc&sni={$sni}#{$encodedLabel}",
            ];
        }

        if ($protocol === 'trojan') {
            return [
                'tls' => "trojan://{$uuid}@{$addr}:443?path=/trojan-ws&security=tls&type=ws&host={$host}&sni={$sni}#{$encodedLabel}",
                'grpc' => "trojan://{$uuid}@{$addr}:443?mode=gun&security=tls&type=grpc&serviceName=trojan-grpc&sni={$sni}#{$encodedLabel}",
            ];
        }

        // shadowsocks
        $ssCred = base64_encode("aes-128-gcm:{$uuid}");
        return [
            'tls' => "ss://{$ssCred}@{$addr}:443?path=/ss-ws&security=tls&host={$host}&type=ws&sni={$sni}#{$encodedLabel}",
            'grpc' => "ss://{$ssCred}@{$addr}:443?mode=gun&security=tls&type=grpc&serviceName=ss-grpc&sni={$sni}#{$encodedLabel}",
        ];
    }

    private function formatXrayText(
        string $protocol,
        string $username,
        string $domain,
        string $uuid,
        int $quotaGb,
        int $ipLimit,
        string $expiredAt,
        array $links
    ): string {
        $protoUpper = strtoupper($protocol);
        $quotaText = $quotaGb > 0 ? "{$quotaGb} GB" : 'Unlimited';

        $lines = [
            "=== {$protoUpper} ACCOUNT ===",
            "Username : {$username}",
            "Domain   : {$domain}",
            "UUID     : {$uuid}",
            "Quota    : {$quotaText}",
            "IP Limit : {$ipLimit} IP",
            "Expired  : {$expiredAt}",
        ];

        if (!empty($links['tls'])) {
            $lines[] = '';
            $lines[] = 'Link TLS (443):';
            $lines[] = $links['tls'];
        }
        if (!empty($links['ntls'])) {
            $lines[] = '';
            $lines[] = 'Link Non-TLS (80):';
            $lines[] = $links['ntls'];
        }
        if (!empty($links['grpc'])) {
            $lines[] = '';
            $lines[] = 'Link gRPC (443):';
            $lines[] = $links['grpc'];
        }

        return implode("\n", $lines);
    }

    private function formatSshText(array $sshInfo, string $expiredAt, int $ipLimit): string
    {
        $lines = [
            '=== SSH ACCOUNT ===',
            'Host     : ' . ($sshInfo['host'] ?: '-'),
            'Username : ' . $sshInfo['username'],
        ];
        if (!empty($sshInfo['password'])) {
            $lines[] = 'Password : ' . $sshInfo['password'];
        }
        $lines[] = 'OpenSSH  : 22';
        $lines[] = 'WS TLS   : 443';
        $lines[] = 'WS NTLS  : 80';
        $lines[] = 'Dropbear : 109, 143';
        $lines[] = 'UDP      : 1-65535';
        $lines[] = "IP Limit : {$ipLimit} IP";
        $lines[] = "Expired  : {$expiredAt}";
        $lines[] = '';
        $lines[] = 'Payload WS:';
        $lines[] = $sshInfo['ws_payload'];

        return implode("\n", $lines);
    }

    /**
     * Collect live Upload (uplink_bytes) & Download (downlink_bytes) per username
     * from BOTH Xray StatsService (127.0.0.1:10000) and SSH iptables mangle CONNMARK accounting.
     */
    public function getTrafficStats(): array
    {
        $py = <<<'PYTHON'
import json
import os
import re
import shutil
import subprocess

traffic = {}

def add_bytes(user, field, val):
    user = (user or "").strip()
    if not user or val < 0:
        return
    entry = traffic.setdefault(user, {"uplink_bytes": 0, "downlink_bytes": 0})
    entry[field] = max(entry[field], int(val))

# 1. Xray StatsService (127.0.0.1:10000) — fast read-only gRPC statsquery
xray_bin = shutil.which("xray")
if not xray_bin:
    for cand in ("/usr/local/bin/xray", "/usr/bin/xray", "/sbin/xray"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            xray_bin = cand
            break
xray_ok = False
if xray_bin:
    out = ""
    for args in (
        [xray_bin, "api", "statsquery", "--server=127.0.0.1:10000", "--pattern", "user>>>"],
        [xray_bin, "api", "statsquery", "-s", "127.0.0.1:10000", "-pattern", "user>>>"],
    ):
        try:
            out = subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=5)
            xray_ok = True
            break
        except Exception:
            continue
    if xray_ok and out:
        try:
            parsed = json.loads(out)
            for item in parsed.get("stat", []) or []:
                name = str(item.get("name", ""))
                val = int(item.get("value", 0) or 0)
                m = re.match(r"^user>>>([^>]+)>>>traffic>>>(uplink|downlink)$", name)
                if m:
                    add_bytes(m.group(1), m.group(2) + "_bytes", val)
        except Exception:
            cur_name = None
            for line in out.splitlines():
                m_name = re.search(r'"?name"?\s*[:=]\s*"?user>>>([^">]+)>>>traffic>>>(uplink|downlink)"?', line)
                if m_name:
                    cur_name = (m_name.group(1), m_name.group(2) + "_bytes")
                    continue
                if cur_name:
                    m_val = re.search(r'"?value"?\s*[:=]\s*"?(\d+)"?', line)
                    if m_val:
                        add_bytes(cur_name[0], cur_name[1], int(m_val.group(1)))
                        cur_name = None

# 2. SSH Kernel Accounting (non-blocking iptables mangle VPN_SSH_UP / VPN_SSH_DOWN)
ssh_sync = "/usr/local/sbin/vpn-ssh-traffic-sync"
if os.path.isfile(ssh_sync) and os.access(ssh_sync, os.X_OK):
    try:
        subprocess.run([ssh_sync], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
    except Exception:
        pass

ssh_ok = False
iptables_bin = shutil.which("iptables")
if iptables_bin:
    for chain, field, prefix in (
        ("VPN_SSH_UP", "uplink_bytes", "vpn_ssh_up:"),
        ("VPN_SSH_DOWN", "downlink_bytes", "vpn_ssh_down:"),
    ):
        try:
            out = subprocess.check_output(
                [iptables_bin, "-t", "mangle", "-L", chain, "-v", "-x", "-n"],
                text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            ssh_ok = True
            for line in out.splitlines():
                parts = line.split()
                if len(parts) < 3 or not parts[1].isdigit():
                    continue
                m_cmt = re.search(r"/\*\s*" + re.escape(prefix) + r"([^\s*]+)\s*\*/", line)
                if m_cmt:
                    add_bytes(m_cmt.group(1), field, int(parts[1]))
        except Exception:
            pass

print(json.dumps({
    "xray_stats_ok": xray_ok,
    "ssh_stats_ok": ssh_ok,
    "accounts": traffic,
}))
PYTHON;

        $res = $this->vpn->runPython($py);
        $parsed = json_decode((string) ($res['output'] ?? ''), true);

        if (!is_array($parsed)) {
            return [
                'xray_stats_ok' => false,
                'ssh_stats_ok' => false,
                'accounts' => [],
            ];
        }

        return [
            'xray_stats_ok' => (bool) ($parsed['xray_stats_ok'] ?? false),
            'ssh_stats_ok' => (bool) ($parsed['ssh_stats_ok'] ?? false),
            'accounts' => is_array($parsed['accounts'] ?? null) ? $parsed['accounts'] : [],
        ];
    }

    /**
     * Collect active/recent device IPs, strike count, and IP limit violation logs for a single account.
     */
    public function getAccountDevices(string $protocol, string $username, int $windowMinutes = 60): array
    {
        $protocol = $this->assertProtocol($protocol);
        $username = $this->assertUsername($username);
        $windowMinutes = max(5, min(1440, $windowMinutes));

        $payloadB64 = base64_encode(json_encode([
            'protocol' => $protocol,
            'username' => $username,
            'window_minutes' => $windowMinutes,
        ]));

        $py = <<<PYTHON
import base64
import datetime
import ipaddress
import json
import os
import re
import subprocess
import time

cfg = json.loads(base64.b64decode("{$payloadB64}").decode("utf-8"))
proto = cfg["protocol"]
target = cfg["username"]
window_sec = int(cfg["window_minutes"]) * 60
now_ts = time.time()
cutoff_ts = now_ts - window_sec
online_cutoff = now_ts - 300

# Read configured IP limit & current strike count
ip_limit = 1
limit_file = f"/etc/kyt/limit/{proto}/ip/{target}"
if os.path.isfile(limit_file):
    try:
        v = int(open(limit_file, "r", encoding="utf-8", errors="ignore").read().strip())
        if v > 0:
            ip_limit = v
    except Exception:
        pass

current_strikes = 0
state_file = f"/etc/kyt/limit/.state/{proto}/{target}.state"
if os.path.isfile(state_file):
    try:
        first_tok = open(state_file, "r", encoding="utf-8", errors="ignore").read().strip().split()[0]
        current_strikes = max(0, int(first_tok))
    except Exception:
        pass

devices = {}

loopback_devices = {}

def record_into(bucket, ip_str, source, ts_val, is_online_flag=False):
    ip_str = (ip_str or "").strip()
    if not ip_str:
        return
    entry = bucket.get(ip_str)
    ts_fmt = datetime.datetime.fromtimestamp(ts_val).strftime("%Y-%m-%d %H:%M:%S") if ts_val else "-"
    if not entry:
        bucket[ip_str] = {
            "ip": ip_str,
            "source": source,
            "is_online": bool(is_online_flag or (ts_val and ts_val >= online_cutoff)),
            "hits": 1,
            "first_seen": ts_fmt,
            "last_seen": ts_fmt,
            "_first_ts": ts_val or 0,
            "_last_ts": ts_val or 0,
        }
    else:
        entry["hits"] += 1
        if is_online_flag or (ts_val and ts_val >= online_cutoff):
            entry["is_online"] = True
        if ts_val:
            if not entry["_first_ts"] or ts_val < entry["_first_ts"]:
                entry["_first_ts"] = ts_val
                entry["first_seen"] = ts_fmt
            if ts_val > entry["_last_ts"]:
                entry["_last_ts"] = ts_val
                entry["last_seen"] = ts_fmt

def record_device(ip_str, source, ts_val, is_online_flag=False):
    record_into(devices, ip_str, source, ts_val, is_online_flag)

if proto != "ssh":
    log_path = "/var/log/xray/access.log"
    if os.path.isfile(log_path):
        line_re = re.compile(
            r"^(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})(?:\.\d+)?\s+"
            r"(?:from\s+)?(?:(?:tcp|udp):)?(\[[0-9a-fA-F:]+\]|[0-9.]+)(?::\d+)?\s+"
        )
        email_re = re.compile(r"(?:^|\s)email:\s*([^\s,;]+)")
        word_re = re.compile(r"(?:^|[\s:\[])" + re.escape(target) + r"(?:$|[\s,;\]])")
        ts_cache = {}
        try:
            with open(log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                start = max(0, size - 8 * 1024 * 1024)
                f.seek(start)
                if start > 0:
                    f.readline()
                raw = f.read().decode("utf-8", errors="ignore")
            for line in raw.splitlines():
                if target not in line:
                    continue
                em = email_re.search(line)
                if em:
                    if em.group(1).strip() != target:
                        continue
                elif not word_re.search(line):
                    continue
                m = line_re.match(line)
                if not m:
                    continue
                ts_key = m.group(1) + " " + m.group(2)
                ts_val = ts_cache.get(ts_key)
                if ts_val is None:
                    try:
                        ts_val = datetime.datetime.strptime(ts_key, "%Y/%m/%d %H:%M:%S").timestamp()
                    except ValueError:
                        continue
                    ts_cache[ts_key] = ts_val
                if ts_val < cutoff_ts:
                    continue
                raw_ip = m.group(3).strip("[]")
                try:
                    ip_obj = ipaddress.ip_address(raw_ip)
                    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
                        ip_obj = ip_obj.ipv4_mapped
                except ValueError:
                    continue
                if ip_obj.is_unspecified:
                    continue
                if ip_obj.is_loopback:
                    record_into(loopback_devices, f"{ip_obj} (Proxy Lokal)", "xray-local", ts_val)
                    continue
                record_device(str(ip_obj), "xray", ts_val)
        except OSError:
            pass
else:
    # SSH: Dropbear, OpenSSH, who, OpenVPN
    db_pids, sshd_pids = set(), set()
    try:
        ps_out = subprocess.check_output(["ps", "-eo", "pid=,ppid=,comm="], text=True, stderr=subprocess.DEVNULL)
        for line in ps_out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
                pid, ppid, comm = int(parts[0]), int(parts[1]), parts[2].lower()
                if comm == "dropbear" and ppid > 1:
                    db_pids.add(pid)
                elif comm == "sshd" and ppid > 1:
                    sshd_pids.add(pid)
    except Exception:
        pass

    log_lines = []
    for lp in ("/var/log/auth.log", "/var/log/secure"):
        if os.path.isfile(lp):
            try:
                with open(lp, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    sz = f.tell()
                    f.seek(max(0, sz - 4 * 1024 * 1024))
                    log_lines.extend(f.read().decode("utf-8", errors="ignore").splitlines())
            except OSError:
                pass
    if not log_lines:
        try:
            jout = subprocess.check_output(
                ["journalctl", "-u", "dropbear", "-u", "ssh", "-u", "sshd", "--since", "24 hours ago", "--no-pager"],
                text=True, stderr=subprocess.DEVNULL
            )
            log_lines.extend(jout.splitlines())
        except Exception:
            pass

    db_re = re.compile(r"dropbear\[(\d+)\].*Password auth succeeded for ['\"]?([^'\"\s]+)['\"]?\s+from\s+([^\s]+)", re.IGNORECASE)
    ssh_re = re.compile(r"sshd\[(\d+)\].*Accepted\s+\S+\s+for\s+([^\s]+)\s+from\s+([^\s]+)", re.IGNORECASE)
    for line in log_lines:
        m = db_re.search(line)
        if m and m.group(2) == target:
            pid = int(m.group(1))
            raw_ip = m.group(3).split(":")[0]
            label = f"SSH-WS (PID {pid})" if raw_ip.startswith("127.") else raw_ip
            record_device(label, "dropbear", now_ts, is_online_flag=(pid in db_pids))
            continue
        m2 = ssh_re.search(line)
        if m2 and m2.group(2) == target:
            pid = int(m2.group(1))
            raw_ip = m2.group(3).split(":")[0]
            label = f"OpenSSH-WS (PID {pid})" if raw_ip.startswith("127.") else raw_ip
            record_device(label, "openssh", now_ts, is_online_flag=(pid in sshd_pids))

    try:
        who_out = subprocess.check_output(["who"], text=True, stderr=subprocess.DEVNULL)
        for line in who_out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == target:
                ip = parts[4].strip("()")
                if ip and not ip.startswith("127."):
                    record_device(ip, "tty", now_ts, is_online_flag=True)
    except Exception:
        pass

    for ovpn_log in ("/etc/openvpn/server/openvpn-tcp.log", "/etc/openvpn/server/openvpn-udp.log"):
        if os.path.isfile(ovpn_log):
            try:
                for line in open(ovpn_log, "r", encoding="utf-8", errors="ignore"):
                    if line.startswith("CLIENT_LIST,"):
                        cols = line.strip().split(",")
                        if len(cols) >= 3 and cols[1] == target:
                            ip = cols[2].split(":")[0]
                            if ip:
                                record_device(ip, "openvpn", now_ts, is_online_flag=True)
            except OSError:
                pass

# Read last 10 violation log entries for this user
violations = []
vlog = "/root/log-limit.txt"
if os.path.isfile(vlog):
    try:
        with open(vlog, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-500:]
        for line in reversed(lines):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1].lower() == proto and parts[2] == target:
                violations.append(line.strip())
                if len(violations) >= 10:
                    break
    except OSError:
        pass

loopback_only = False
if not devices and loopback_devices:
    devices = loopback_devices
    loopback_only = True

sorted_devices = sorted(
    devices.values(),
    key=lambda d: (0 if d["is_online"] else 1, -d["_last_ts"], -d["hits"]),
)
for d in sorted_devices:
    d.pop("_first_ts", None)
    d.pop("_last_ts", None)

active_count = sum(1 for d in sorted_devices if d["is_online"])

print(json.dumps({
    "protocol": proto,
    "username": target,
    "window_minutes": int(cfg["window_minutes"]),
    "ip_limit": ip_limit,
    "active_device_count": active_count,
    "recent_device_count": len(sorted_devices),
    "current_strikes": current_strikes,
    "loopback_only": loopback_only,
    "devices": sorted_devices[:50],
    "violations": violations,
}))
PYTHON;

        $res = $this->vpn->runPython($py);
        $parsed = json_decode((string) ($res['output'] ?? ''), true);

        if (!is_array($parsed)) {
            return [
                'protocol' => $protocol,
                'username' => $username,
                'window_minutes' => $windowMinutes,
                'ip_limit' => 1,
                'active_device_count' => 0,
                'recent_device_count' => 0,
                'current_strikes' => 0,
                'devices' => [],
                'violations' => [],
            ];
        }

        return $parsed;
    }
}
