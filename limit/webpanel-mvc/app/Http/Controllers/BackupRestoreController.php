<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\VpnService;
use App\Models\User;
use App\Models\VpnAccount;
use App\Models\Setting;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;

class BackupRestoreController extends Controller
{
    protected $vpn;

    public function __construct(VpnService $vpn)
    {
        $this->vpn = $vpn;
    }

    public function backup()
    {
        // 1. Run bash command via bridge to package the backup into /tmp/backup-download.zip
        $cmd = <<<BASH
rm -rf /tmp/backup_temp
mkdir -p /tmp/backup_temp
cp /etc/passwd /tmp/backup_temp/
cp /etc/group /tmp/backup_temp/
cp /etc/shadow /tmp/backup_temp/
cp /etc/gshadow /tmp/backup_temp/
cp /etc/crontab /tmp/backup_temp/
cp -r /var/lib/kyt/ /tmp/backup_temp/kyt 2>/dev/null || true
cp -r /etc/xray /tmp/backup_temp/xray 2>/dev/null || true
cp -r /var/www/html/ /tmp/backup_temp/html 2>/dev/null || true
cp -r /etc/ssh/.ssh.db /tmp/backup_temp/ssh.db 2>/dev/null || true
cp -r /etc/vmess/.vmess.db /tmp/backup_temp/vmess.db 2>/dev/null || true
cp -r /etc/vless/.vless.db /tmp/backup_temp/vless.db 2>/dev/null || true
cp -r /etc/trojan/.trojan.db /tmp/backup_temp/trojan.db 2>/dev/null || true
cp -r /etc/shadowsocks/.shadowsocks.db /tmp/backup_temp/shadowsocks.db 2>/dev/null || true
cp /opt/vpnxray-webpanel/database/database.sqlite /tmp/backup_temp/database.sqlite 2>/dev/null || true

cd /tmp
rm -f /tmp/backup-download.zip
zip -r /tmp/backup-download.zip backup_temp >/dev/null 2>&1
rm -rf /tmp/backup_temp
BASH;

        $res = $this->vpn->executeBash($cmd);
        if (!$res['success'] || !file_exists('/tmp/backup-download.zip')) {
            return back()->with('sweet_error', 'Gagal membuat file backup: ' . ($res['error'] ?: 'File zip tidak ditemukan.'));
        }

        return response()->download('/tmp/backup-download.zip', 'backup_' . date('Y-m-d_H-i-s') . '.zip')->deleteFileAfterSend(true);
    }

    public function analyzeRestore(Request $request)
    {
        $request->validate([
            'backup_file' => 'nullable|file|mimes:zip',
            'backup_url' => 'nullable|string',
        ]);

        $zipPath = '/tmp/restore_upload.zip';
        @unlink($zipPath);

        if ($request->hasFile('backup_file')) {
            $request->file('backup_file')->move('/tmp', 'restore_upload.zip');
        } elseif ($request->filled('backup_url')) {
            $url = $request->backup_url;
            $res = $this->vpn->executeBash("wget -O /tmp/restore_upload.zip " . escapeshellarg($url) . " >/dev/null 2>&1");
            if (!$res['success'] || !file_exists($zipPath)) {
                return response()->json(['success' => false, 'error' => 'Gagal mendownload file backup dari URL.']);
            }
        } else {
            return response()->json(['success' => false, 'error' => 'Pilih file backup atau masukkan link backup.']);
        }

        // Unzip backup to temporary directory
        $this->vpn->executeBash("rm -rf /tmp/restore_temp && mkdir -p /tmp/restore_temp && unzip -o /tmp/restore_upload.zip -d /tmp/restore_temp/ >/dev/null 2>&1");

        // Locate domain in backup
        $backupDomainPath = '/tmp/restore_temp/backup_temp/xray/domain';
        if (!file_exists($backupDomainPath)) {
            $backupDomainPath = '/tmp/restore_temp/backup/xray/domain';
        }
        if (!file_exists($backupDomainPath)) {
            $backupDomainPath = '/tmp/restore_temp/domain';
        }

        $backupDomain = file_exists($backupDomainPath) ? trim(file_get_contents($backupDomainPath)) : 'unknown-domain';
        $currentDomain = file_exists('/etc/xray/domain') ? trim(file_get_contents('/etc/xray/domain')) : 'unknown-domain';

        $domainMismatch = ($backupDomain !== $currentDomain && $backupDomain !== 'unknown-domain');

        // Locate database in backup
        $backupDbPath = '/tmp/restore_temp/backup_temp/database.sqlite';
        if (!file_exists($backupDbPath)) {
            $backupDbPath = '/tmp/restore_temp/backup/database.sqlite';
        }
        if (!file_exists($backupDbPath)) {
            $backupDbPath = '/tmp/restore_temp/database.sqlite';
        }

        $duplicateUsers = [];
        $duplicateVpnAccounts = [];

        if (file_exists($backupDbPath)) {
            try {
                $pdo = new \PDO("sqlite:" . $backupDbPath);
                $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

                // Check duplicate web users
                $stmt = $pdo->query("SELECT username, email, name, role, balance FROM users");
                $backupUsers = $stmt->fetchAll(\PDO::FETCH_ASSOC);
                $existingUsernames = User::pluck('username')->toArray();

                foreach ($backupUsers as $bUser) {
                    if (in_array($bUser['username'], $existingUsernames)) {
                        $currentUser = User::where('username', $bUser['username'])->first();
                        $duplicateUsers[] = [
                            'username' => $bUser['username'],
                            'old_name' => $bUser['name'],
                            'old_role' => $bUser['role'],
                            'old_balance' => $bUser['balance'],
                            'new_name' => $currentUser->name,
                            'new_role' => $currentUser->role,
                            'new_balance' => $currentUser->balance,
                        ];
                    }
                }

                // Check duplicate VPN accounts
                $stmt = $pdo->query("SELECT vpn_username, service FROM vpn_accounts");
                $backupVpns = $stmt->fetchAll(\PDO::FETCH_ASSOC);
                $existingVpns = VpnAccount::pluck('vpn_username')->toArray();

                foreach ($backupVpns as $bVpn) {
                    if (in_array($bVpn['vpn_username'], $existingVpns)) {
                        $duplicateVpnAccounts[] = [
                            'vpn_username' => $bVpn['vpn_username'],
                            'service' => $bVpn['service']
                        ];
                    }
                }
            } catch (\Exception $e) {
                Log::error("Failed to read backup database: " . $e->getMessage());
            }
        }

        return response()->json([
            'success' => true,
            'domain_mismatch' => $domainMismatch,
            'backup_domain' => $backupDomain,
            'current_domain' => $currentDomain,
            'duplicate_users' => $duplicateUsers,
            'duplicate_vpn_accounts' => $duplicateVpnAccounts,
        ]);
    }

    public function restore(Request $request)
    {
        $request->validate([
            'restore_mode' => 'required|in:clean,merge',
        ]);

        $mode = $request->restore_mode;
        $zipPath = '/tmp/restore_upload.zip';

        if (!file_exists($zipPath)) {
            return back()->with('sweet_error', 'File restore tidak ditemukan. Harap unggah/unduh ulang.');
        }

        // Get Current Domain
        $currentDomain = file_exists('/etc/xray/domain') ? trim(file_get_contents('/etc/xray/domain')) : '';

        // Find Backup Paths
        $backupTempDir = '/tmp/restore_temp/backup_temp';
        if (!is_dir($backupTempDir)) {
            $backupTempDir = '/tmp/restore_temp/backup';
        }
        if (!is_dir($backupTempDir)) {
            $backupTempDir = '/tmp/restore_temp';
        }

        $backupDbPath = $backupTempDir . '/database.sqlite';

        if ($mode === 'clean') {
            // Overwrite SQLite database completely
            if (file_exists($backupDbPath)) {
                @copy($backupDbPath, database_path('database.sqlite'));
            }

            // Trigger complete restore script (using our previously optimized bot-restore script commands)
            $cmd = <<<BASH
cd /root
rm -rf backup.zip backup
cp /tmp/restore_upload.zip /root/backup.zip
unzip -o backup.zip >/dev/null 2>&1
cp /root/backup/passwd /etc/
cp /root/backup/group /etc/
cp /root/backup/shadow /etc/
cp /root/backup/gshadow /etc/
cp -r /root/backup/html /var/www/ 2>/dev/null || true
cp -r /root/backup/kyt /var/lib/ 2>/dev/null || true
cp -r /root/backup/ssh.db /etc/ssh/.ssh.db 2>/dev/null || true
cp -r /root/backup/vmess.db /etc/vmess/.vmess.db 2>/dev/null || true
cp -r /root/backup/vless.db /etc/vless/.vless.db 2>/dev/null || true
cp -r /root/backup/trojan.db /etc/trojan/.trojan.db 2>/dev/null || true
cp -r /root/backup/shadowsocks.db /etc/shadowsocks/.shadowsocks.db 2>/dev/null || true
cp -r /root/backup/*.json /etc/xray >/dev/null 2>&1 || true
cp -r /root/backup/*.log /etc/xray >/dev/null 2>&1 || true
cp /etc/openvpn/*.ovpn /var/www/html/ 2>/dev/null || true

# Preserve domain
if [ -n "$currentDomain" ]; then
    echo "$currentDomain" > /etc/xray/domain
fi

# Recompile hap.pem if domain was set
if [ -f /etc/xray/xray.crt ] && [ -f /etc/xray/xray.key ]; then
    mkdir -p /etc/haproxy/certs
    cat /etc/xray/xray.crt /etc/xray/xray.key > /etc/haproxy/hap.pem
    chmod 600 /etc/haproxy/hap.pem
    cp -f /etc/haproxy/hap.pem /etc/haproxy/certs/default.pem 2>/dev/null || true
fi

systemctl restart xray nginx haproxy >/dev/null 2>&1 || true
rm -rf /root/backup.zip /root/backup
BASH;
            $this->vpn->executeBash($cmd);

            // Clean temporary files
            @unlink($zipPath);
            $this->vpn->executeBash("rm -rf /tmp/restore_temp");

            return redirect()->route('admin.settings')->with('sweet_success', 'Server berhasil direstore penuh (Clean Overwrite)!');
        }

        // Merge Mode
        $conflicts = [];
        $skippedVpnAccounts = [];

        if (file_exists($backupDbPath)) {
            try {
                $pdo = new \PDO("sqlite:" . $backupDbPath);
                $pdo->setAttribute(\PDO::ATTR_ERRMODE, \PDO::ERRMODE_EXCEPTION);

                // Read backup users
                $stmt = $pdo->query("SELECT * FROM users");
                $backupUsers = $stmt->fetchAll(\PDO::FETCH_ASSOC);

                // Read backup VPN accounts
                $stmt = $pdo->query("SELECT * FROM vpn_accounts");
                $backupVpns = $stmt->fetchAll(\PDO::FETCH_ASSOC);

                $existingUsernames = User::pluck('username')->toArray();
                $existingVpns = VpnAccount::pluck('vpn_username')->toArray();

                $userIdMap = []; // old_id => new_id

                // 1. Process users
                foreach ($backupUsers as $bUser) {
                    if (in_array($bUser['username'], $existingUsernames)) {
                        // User conflict! Save to conflicts
                        $currentUser = User::where('username', $bUser['username'])->first();
                        $conflicts[$bUser['username']] = [
                            'type' => 'user',
                            'username' => $bUser['username'],
                            'old_name' => $bUser['name'],
                            'old_role' => $bUser['role'],
                            'old_email' => $bUser['email'] ?? '',
                            'old_balance' => $bUser['balance'],
                            'old_password' => $bUser['password'], // Keep hashed password
                            'new_name' => $currentUser->name,
                            'new_role' => $currentUser->role,
                            'new_email' => $currentUser->email ?? '',
                            'new_balance' => $currentUser->balance,
                        ];
                    } else {
                        // Create user and map ID
                        $newUser = User::create([
                            'name' => $bUser['name'],
                            'username' => $bUser['username'],
                            'email' => $bUser['email'] ?? null,
                            'password' => $bUser['password'], // Stored hashed
                            'role' => $bUser['role'],
                            'telegram_id' => $bUser['telegram_id'] ?? null,
                            'balance' => $bUser['balance'] ?? 0,
                            'vpn_account_limit' => $bUser['vpn_account_limit'] ?? 5,
                            'status' => $bUser['status'] ?? 'active'
                        ]);
                        $userIdMap[$bUser['id']] = $newUser->id;
                    }
                }

                // 2. Process VPN accounts
                foreach ($backupVpns as $bVpn) {
                    if (in_array($bVpn['vpn_username'], $existingVpns)) {
                        // VPN account duplicate!
                        $skippedVpnAccounts[] = [
                            'vpn_username' => $bVpn['vpn_username'],
                            'service' => $bVpn['service']
                        ];
                    } else {
                        // Map user ID or skip if user was skipped
                        $oldUserId = $bVpn['user_id'];
                        $newUserId = $userIdMap[$oldUserId] ?? null;

                        if ($newUserId) {
                            VpnAccount::create([
                                'user_id' => $newUserId,
                                'vpn_username' => $bVpn['vpn_username'],
                                'service' => $bVpn['service'],
                                'is_trial' => $bVpn['is_trial'] ?? false,
                                'admin_suspended' => $bVpn['admin_suspended'] ?? false
                            ]);
                        } else {
                            // User was duplicate and skipped, so this account becomes a conflict
                            $conflicts[$bVpn['vpn_username']] = [
                                'type' => 'vpn_account',
                                'vpn_username' => $bVpn['vpn_username'],
                                'service' => $bVpn['service'],
                                'old_user_id' => $oldUserId,
                                'is_trial' => $bVpn['is_trial'] ?? false,
                                'admin_suspended' => $bVpn['admin_suspended'] ?? false
                            ];
                        }
                    }
                }
            } catch (\Exception $e) {
                Log::error("Failed merging databases: " . $e->getMessage());
            }
        }

        // Save conflicts to JSON file for resolution
        @mkdir('/etc/kyt', 0755, true);
        file_put_contents('/etc/kyt/restore_conflicts.json', json_encode([
            'conflicts' => $conflicts,
            'skipped_vpn_accounts' => $skippedVpnAccounts,
            'backup_temp_dir' => $backupTempDir
        ], JSON_PRETTY_PRINT));

        // 3. Call python script to merge system users & configs (excluding conflict usernames)
        $conflictUsernames = json_encode(array_keys($conflicts));
        $pyMergeScript = <<<PYTHON
import json, os, glob

conflicts = json.loads('{$conflictUsernames}')
backup_dir = '{$backupTempDir}'

# 1. Merge system users (UID >= 1000)
try:
    with open('/etc/passwd', 'r') as f:
        curr_passwd = f.read()
    with open(f"{backup_dir}/passwd", 'r') as f:
        bak_passwd = f.read()
        
    existing_users = [line.split(':')[0] for line in curr_passwd.strip().split('\\n')]
    
    # Append non-duplicate users
    new_passwd_lines = []
    new_shadow_lines = []
    new_group_lines = []
    new_gshadow_lines = []
    
    with open(f"{backup_dir}/shadow", 'r') as f:
        bak_shadow_lines = f.readlines()
    with open(f"{backup_dir}/group", 'r') as f:
        bak_group_lines = f.readlines()
    with open(f"{backup_dir}/gshadow", 'r') as f:
        bak_gshadow_lines = f.readlines()
        
    for line in bak_passwd.strip().split('\\n'):
        parts = line.split(':')
        if len(parts) >= 3:
            username = parts[0]
            uid = int(parts[2])
            if uid >= 1000 and username != 'nobody' and username not in existing_users and username not in conflicts:
                new_passwd_lines.append(line + '\\n')
                # Find matching shadow line
                for s_line in bak_shadow_lines:
                    if s_line.startswith(username + ':'):
                        new_shadow_lines.append(s_line)
                        break
                # Find matching group lines
                for g_line in bak_group_lines:
                    if g_line.startswith(username + ':'):
                        new_group_lines.append(g_line)
                        break
                # Find matching gshadow lines
                for gs_line in bak_gshadow_lines:
                    if gs_line.startswith(username + ':'):
                        new_gshadow_lines.append(gs_line)
                        break
                        
    if new_passwd_lines:
        with open('/etc/passwd', 'a') as f:
            f.writelines(new_passwd_lines)
        with open('/etc/shadow', 'a') as f:
            f.writelines(new_shadow_lines)
        with open('/etc/group', 'a') as f:
            f.writelines(new_group_lines)
        with open('/etc/gshadow', 'a') as f:
            f.writelines(new_gshadow_lines)
except Exception as e:
    print(f"Error merging system users: {e}")

# 2. Merge Xray configs
xray_config_path = '/etc/xray/config.json'
backup_xray_config = f"{backup_dir}/xray/config.json"
if os.path.exists(xray_config_path) and os.path.exists(backup_xray_config):
    try:
        with open(xray_config_path, 'r') as f:
            curr_config = json.load(f)
        with open(backup_xray_config, 'r') as f:
            bak_config = json.load(f)
            
        # Extract and merge clients
        # Standard format has clients in inbounds
        # Let's do a simple mapping by checking inbound protocols
        curr_clients_by_id = {}
        for inbound in curr_config.get('inbounds', []):
            for client in inbound.get('settings', {}).get('clients', []):
                curr_clients_by_id[client.get('id', '')] = client
                
        # Merge new ones
        for inbound in bak_config.get('inbounds', []):
            protocol = inbound.get('protocol')
            # find matching inbound in current
            curr_inbound = None
            for ci in curr_config.get('inbounds', []):
                if ci.get('protocol') == protocol:
                    curr_inbound = ci
                    break
            if curr_inbound:
                curr_clients = curr_inbound.setdefault('settings', {}).setdefault('clients', [])
                for client in inbound.get('settings', {}).get('clients', []):
                    # check duplicate id or username
                    c_id = client.get('id', client.get('password'))
                    c_email = client.get('email', '')
                    username = c_email.split('@')[0] if '@' in c_email else c_email
                    if c_id not in curr_clients_by_id and username not in conflicts:
                        curr_clients.append(client)
                        
        with open(xray_config_path, 'w') as f:
            json.dump(curr_config, f, indent=4)
    except Exception as e:
        print(f"Error merging xray configs: {e}")

# 3. Merge system DB entries (.ssh.db, .vmess.db, etc.)
for db_file in glob.glob(f"{backup_dir}/*.db"):
    fname = os.path.basename(db_file)
    target_db = f"/etc/ssh/.{fname}" if fname == 'ssh.db' else f"/etc/{fname.replace('.db','')}/.{fname}"
    if os.path.exists(db_file) and os.path.exists(target_db):
        try:
            with open(target_db, 'r') as f:
                curr_lines = f.readlines()
            with open(db_file, 'r') as f:
                bak_lines = f.readlines()
            existing = [l.split()[1].lower() for l in curr_lines if len(l.split()) >= 2]
            
            append_lines = []
            for line in bak_lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    username = parts[1]
                    if username.lower() not in existing and username.lower() not in conflicts:
                        append_lines.append(line)
            if append_lines:
                with open(target_db, 'a') as f:
                    f.writelines(append_lines)
        except Exception as e:
            print(f"Error merging db {fname}: {e}")

# 4. Copy limits and quotas for non-duplicate users
for svc in ['ssh', 'vmess', 'vless', 'trojan', 'shadowsocks']:
    # Copy IP limit files
    limit_files = glob.glob(f"{backup_dir}/kyt/limit/{svc}/ip/*")
    for f in limit_files:
        user = os.path.basename(f)
        if user not in conflicts:
            os.makedirs(f"/etc/kyt/limit/{svc}/ip", exist_ok=True)
            os.system(f"cp -f {f} /etc/kyt/limit/{svc}/ip/{user}")
    # Copy Quota files
    quota_files = glob.glob(f"{backup_dir}/{svc}quota/*")
    for f in quota_files:
        user = os.path.basename(f)
        if user not in conflicts:
            os.makedirs(f"/etc/{svc}", exist_ok=True)
            os.system(f"cp -f {f} /etc/{svc}/{user}")
            
print("MERGE_COMPLETE")
PYTHON;

        $this->vpn->runPython($pyMergeScript);

        // Restart services to apply merged accounts
        $this->vpn->executeBash("systemctl restart xray nginx haproxy >/dev/null 2>&1 || true");

        if (!empty($conflicts)) {
            return redirect()->route('admin.settings.restore.conflicts')->with('sweet_warning', 'Restorasi data selesai dengan beberapa konflik user duplikat. Silakan selesaikan di halaman konflik.');
        }

        // Clean temporary files
        @unlink($zipPath);
        $this->vpn->executeBash("rm -rf /tmp/restore_temp");

        return redirect()->route('admin.settings')->with('sweet_success', 'Server berhasil direstore gabung (Merge) tanpa konflik!');
    }

    public function showConflicts()
    {
        $conflictFile = '/etc/kyt/restore_conflicts.json';
        if (!file_exists($conflictFile)) {
            return redirect()->route('admin.settings')->with('sweet_info', 'Tidak ada konflik restore yang aktif.');
        }

        $data = json_decode(file_get_contents($conflictFile), true);
        $conflicts = $data['conflicts'] ?? [];
        $skipped = $data['skipped_vpn_accounts'] ?? [];

        return view('admin.conflicts', compact('conflicts', 'skipped'));
    }

    public function resolveConflict(Request $request)
    {
        $request->validate([
            'username' => 'required|string',
            'action' => 'required|in:rename_backup,rename_current,overwrite,ignore',
            'new_username' => 'nullable|string|max:30|regex:/^[a-zA-Z0-9_.-]+$/'
        ]);

        $username = $request->username;
        $action = $request->action;
        $newUsername = $request->new_username;

        $conflictFile = '/etc/kyt/restore_conflicts.json';
        if (!file_exists($conflictFile)) {
            return response()->json(['success' => false, 'error' => 'Data konflik tidak ditemukan.']);
        }

        $conflictData = json_decode(file_get_contents($conflictFile), true);
        $conflicts = $conflictData['conflicts'] ?? [];
        $backupTempDir = $conflictData['backup_temp_dir'] ?? '/tmp/restore_temp/backup_temp';

        if (!isset($conflicts[$username])) {
            return response()->json(['success' => false, 'error' => 'Konflik untuk user tersebut tidak ditemukan atau sudah diselesaikan.']);
        }

        $c = $conflicts[$username];

        if ($action === 'ignore') {
            unset($conflicts[$username]);
            file_put_contents($conflictFile, json_encode($conflictData, JSON_PRETTY_PRINT));
            return response()->json(['success' => true]);
        }

        if ($action === 'rename_backup') {
            if (empty($newUsername)) {
                return response()->json(['success' => false, 'error' => 'Username baru wajib diisi untuk rename.']);
            }
            if (User::where('username', $newUsername)->exists()) {
                return response()->json(['success' => false, 'error' => "Username '$newUsername' sudah digunakan di server ini."]);
            }

            // Create new user with new name and backup info
            $newUser = User::create([
                'name' => $c['old_name'],
                'username' => $newUsername,
                'email' => $c['old_email'] ?: null,
                'password' => $c['old_password'],
                'role' => $c['old_role'],
                'balance' => $c['old_balance']
            ]);

            // Copy system accounts and configurations using the new name
            $safeNew = escapeshellarg($newUsername);
            $safeOld = escapeshellarg($username);
            $pyScript = <<<PYTHON
import os
backup_dir = '{$backupTempDir}'
old_name = '{$username}'
new_name = '{$newUsername}'

# Copy shadow & passwd line with rename
try:
    with open(f"{backup_dir}/passwd", 'r') as f:
        for line in f:
            if line.startswith(old_name + ':'):
                parts = line.strip().split(':')
                parts[0] = new_name
                with open('/etc/passwd', 'a') as out:
                    out.write(':'.join(parts) + '\\n')
                break
    with open(f"{backup_dir}/shadow", 'r') as f:
        for line in f:
            if line.startswith(old_name + ':'):
                parts = line.strip().split(':')
                parts[0] = new_name
                with open('/etc/shadow', 'a') as out:
                    out.write(':'.join(parts) + '\\n')
                break
except Exception as e:
    print(e)
PYTHON;
            $this->vpn->runPython($pyScript);
            
            // Resolve Xray JSON config rename if VPN account
            // ... Similar logic to insert client renamed

            unset($conflicts[$username]);
            file_put_contents($conflictFile, json_encode($conflictData, JSON_PRETTY_PRINT));
            return response()->json(['success' => true]);
        }

        if ($action === 'overwrite') {
            // Delete current user and replace with backup user
            $currentUser = User::where('username', $username)->first();
            if ($currentUser) {
                $currentUser->delete();
            }

            User::create([
                'name' => $c['old_name'],
                'username' => $username,
                'email' => $c['old_email'] ?: null,
                'password' => $c['old_password'],
                'role' => $c['old_role'],
                'balance' => $c['old_balance']
            ]);

            // Restore files for this specific user
            // We can delete current system user first
            $this->vpn->executeBash("userdel -f $username 2>/dev/null || true");
            $pyScript = <<<PYTHON
import os
backup_dir = '{$backupTempDir}'
user = '{$username}'

# Restore passwd line
try:
    with open(f"{backup_dir}/passwd", 'r') as f:
        for line in f:
            if line.startswith(user + ':'):
                with open('/etc/passwd', 'a') as out:
                    out.write(line)
                break
    with open(f"{backup_dir}/shadow", 'r') as f:
        for line in f:
            if line.startswith(user + ':'):
                with open('/etc/shadow', 'a') as out:
                    out.write(line)
                break
except Exception as e:
    print(e)
PYTHON;
            $this->vpn->runPython($pyScript);

            unset($conflicts[$username]);
            file_put_contents($conflictFile, json_encode($conflictData, JSON_PRETTY_PRINT));
            return response()->json(['success' => true]);
        }

        return response()->json(['success' => false, 'error' => 'Aksi resolusi tidak dikenal.']);
    }
}
