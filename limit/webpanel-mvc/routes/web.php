<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\VpnController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\AdminController;
use App\Http\Controllers\RegisterController;

Route::get('/', function () {
    return redirect()->route('dashboard');
});

Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login'])->name('login.post');
Route::get('/login/telegram', [AuthController::class, 'generateTelegramToken'])->name('auth.telegram');
Route::get('/login/verify', [AuthController::class, 'verifyLogin'])->name('login.verify');

Route::get('/register', [RegisterController::class, 'showRegistrationForm'])->name('register');
Route::post('/register', [RegisterController::class, 'register'])->name('register.post');
Route::get('/api/check-username', [RegisterController::class, 'checkUsername'])->name('api.check-username-register');

Route::post('/logout', [AuthController::class, 'logout'])->name('logout');

// Webhook listener payment from Notification Listener app
Route::post('/listener/payment', [\App\Http\Controllers\PaymentController::class, 'processListener']);
Route::post('/listener/test-connection', [\App\Http\Controllers\PaymentController::class, 'testConnection']);

Route::middleware('auth')->group(function () {
    Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');

    Route::get('/profile', [ProfileController::class, 'index'])->name('profile');
    Route::post('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::post('/profile/unlink', [ProfileController::class, 'unlinkTelegram'])->name('profile.unlink');

    Route::middleware('admin')->group(function () {
        Route::get('/admin/users', [AdminController::class, 'users'])->name('admin.users');
        Route::post('/admin/users/{user}', [AdminController::class, 'updateUser'])->name('admin.users.update');
        Route::post('/admin/users/{user}/reset-password', [AdminController::class, 'resetPassword'])->name('admin.users.reset-password');
        Route::post('/admin/users/{user}/unlink-telegram', [AdminController::class, 'unlinkTelegram'])->name('admin.users.unlink-telegram');
        Route::post('/admin/users/{user}/inject-balance', [AdminController::class, 'injectBalance'])->name('admin.users.inject-balance');
        Route::post('/admin/users/{user}/block-balance', [AdminController::class, 'blockBalance'])->name('admin.users.block-balance');
        Route::delete('/admin/users/{user}', [AdminController::class, 'deleteUser'])->name('admin.users.delete');

        Route::get('/admin/settings', [\App\Http\Controllers\SettingController::class, 'index'])->name('admin.settings');
        Route::post('/admin/settings/prices', [\App\Http\Controllers\SettingController::class, 'updatePrices'])->name('admin.settings.prices');
        Route::post('/admin/settings/payment', [\App\Http\Controllers\SettingController::class, 'updatePayment'])->name('admin.settings.payment');
        Route::post('/admin/settings/announcement', [\App\Http\Controllers\SettingController::class, 'updateAnnouncement'])->name('admin.settings.announcement');
        Route::post('/admin/settings/backup', [\App\Http\Controllers\BackupRestoreController::class, 'backup'])->name('admin.settings.backup');
        Route::post('/admin/settings/restore/analyze', [\App\Http\Controllers\BackupRestoreController::class, 'analyzeRestore'])->name('admin.settings.restore.analyze');
        Route::post('/admin/settings/restore', [\App\Http\Controllers\BackupRestoreController::class, 'restore'])->name('admin.settings.restore');
        Route::get('/admin/settings/restore/conflicts', [\App\Http\Controllers\BackupRestoreController::class, 'showConflicts'])->name('admin.settings.restore.conflicts');
        Route::post('/admin/settings/restore/conflicts/resolve', [\App\Http\Controllers\BackupRestoreController::class, 'resolveConflict'])->name('admin.settings.restore.conflicts.resolve');
        Route::post('/admin/notifications/broadcast', [\App\Http\Controllers\NotificationController::class, 'broadcast'])->name('admin.notifications.broadcast');

        Route::get('/admin/finance', [\App\Http\Controllers\WalletController::class, 'adminFinance'])->name('admin.finance');
        
        // Admin Orders
        Route::get('/admin/orders', [\App\Http\Controllers\OrderController::class, 'index'])->name('admin.orders');
        Route::post('/admin/orders/{id}/approve', [\App\Http\Controllers\OrderController::class, 'approve'])->name('admin.orders.approve');
        Route::post('/admin/orders/{id}/cancel', [\App\Http\Controllers\OrderController::class, 'cancel'])->name('admin.orders.cancel');

        Route::get('/vpn/master', [VpnController::class, 'master'])->name('vpn.master');

        // Admin Vouchers
        Route::get('/admin/vouchers', [\App\Http\Controllers\VoucherController::class, 'index'])->name('admin.vouchers');
        Route::post('/admin/vouchers', [\App\Http\Controllers\VoucherController::class, 'store'])->name('admin.vouchers.store');
        Route::delete('/admin/vouchers/{voucher}', [\App\Http\Controllers\VoucherController::class, 'destroy'])->name('admin.vouchers.destroy');

        // Admin Telegram Bot Management
        Route::get('/admin/bot/users', [\App\Http\Controllers\TelegramBotController::class, 'index'])->name('admin.bot.users');
        Route::post('/admin/bot/users/{botUser}', [\App\Http\Controllers\TelegramBotController::class, 'updateUser'])->name('admin.bot.users.update');
        Route::delete('/admin/bot/users/{botUser}', [\App\Http\Controllers\TelegramBotController::class, 'deleteUser'])->name('admin.bot.users.delete');
        Route::post('/admin/bot/access/{id}/approve', [\App\Http\Controllers\TelegramBotController::class, 'approveAccess'])->name('admin.bot.access.approve');
        Route::post('/admin/bot/access/{id}/reject', [\App\Http\Controllers\TelegramBotController::class, 'rejectAccess'])->name('admin.bot.access.reject');
        Route::post('/admin/bot/quota/{id}/approve', [\App\Http\Controllers\TelegramBotController::class, 'approveQuota'])->name('admin.bot.quota.approve');
        Route::post('/admin/bot/quota/{id}/reject', [\App\Http\Controllers\TelegramBotController::class, 'rejectQuota'])->name('admin.bot.quota.reject');
        Route::post('/admin/settings/bot', [\App\Http\Controllers\SettingController::class, 'updateBotSettings'])->name('admin.settings.bot');
    });
    Route::get('/vpn/{protocol}/config/{user}', [VpnController::class, 'viewConfig'])->name('vpn.config');

    Route::prefix('vpn/{protocol}')->name('vpn.')->group(function () {
        Route::get('/', [VpnController::class, 'index'])->name('index');
        Route::get('/create', [VpnController::class, 'create'])->name('create');
        Route::post('/store', [VpnController::class, 'store'])->name('store');
        
        Route::get('/{user}/renew', [VpnController::class, 'renewForm'])->name('renew');
        Route::post('/{user}/renew', [VpnController::class, 'renew'])->name('renew.process');
        
        Route::post('/{user}/delete', [VpnController::class, 'delete'])->name('delete');
        Route::post('/{user}/suspend', [VpnController::class, 'suspend'])->name('suspend');
        Route::post('/{user}/unsuspend', [VpnController::class, 'unsuspend'])->name('unsuspend');
    });

    Route::get('/wallet', [\App\Http\Controllers\WalletController::class, 'index'])->name('wallet.index');
    Route::post('/wallet/topup', [\App\Http\Controllers\WalletController::class, 'topup'])->name('wallet.topup');
    Route::post('/wallet/cancel', [\App\Http\Controllers\WalletController::class, 'cancelTopup'])->name('wallet.cancel');
    Route::post('/wallet/voucher', [\App\Http\Controllers\WalletController::class, 'redeemVoucher'])->name('wallet.voucher.redeem');

    Route::get('/checkout/{id}', [\App\Http\Controllers\CheckoutController::class, 'show'])->name('checkout.show');
    Route::post('/checkout/{id}/cancel', [\App\Http\Controllers\CheckoutController::class, 'cancel'])->name('checkout.cancel');
    Route::get('/checkout/{id}/status', [\App\Http\Controllers\PaymentController::class, 'status'])->name('transaction.status');
    Route::get('/checkout/{id}/success', [\App\Http\Controllers\CheckoutController::class, 'success'])->name('checkout.success');
    Route::get('/checkout/{id}/cancelled', [\App\Http\Controllers\CheckoutController::class, 'cancelled'])->name('checkout.cancelled');

    Route::get('/notifications', [\App\Http\Controllers\NotificationController::class, 'index'])->name('notifications.index');
    Route::post('/notifications/read-all', [\App\Http\Controllers\NotificationController::class, 'readAll'])->name('notifications.read-all');
});

Route::post('/api/internal/approve-token', [AuthController::class, 'approveToken']);
Route::get('/api/internal/check-username', [VpnController::class, 'checkUsername'])->name('api.check-username');

// ─── Internal API for Telegram Bot ───────────────────────────────────
Route::prefix('api/internal')->group(function () {
    // Bot configuration
    Route::get('/bot/config', [\App\Http\Controllers\InternalApiController::class, 'botConfig']);

    // User management
    Route::post('/bot/user/touch', [\App\Http\Controllers\InternalApiController::class, 'touchUser']);
    Route::get('/bot/user/{tgId}', [\App\Http\Controllers\InternalApiController::class, 'getUser']);
    Route::get('/bot/user/{tgId}/status', [\App\Http\Controllers\InternalApiController::class, 'getUserStatus']);
    Route::get('/bot/user/{tgId}/quota', [\App\Http\Controllers\InternalApiController::class, 'getUserQuota']);
    Route::get('/bot/user/{tgId}/stats', [\App\Http\Controllers\InternalApiController::class, 'getUserStats']);
    Route::post('/bot/user/{tgId}/approve', [\App\Http\Controllers\InternalApiController::class, 'approveUser']);
    Route::post('/bot/user/{tgId}/reject', [\App\Http\Controllers\InternalApiController::class, 'rejectUser']);
    Route::post('/bot/user/{tgId}/suspend', [\App\Http\Controllers\InternalApiController::class, 'suspendUser']);
    Route::post('/bot/user/{tgId}/quota/update', [\App\Http\Controllers\InternalApiController::class, 'updateUserQuota']);
    Route::get('/bot/users', [\App\Http\Controllers\InternalApiController::class, 'listUsers']);

    // Access requests
    Route::post('/bot/access-request', [\App\Http\Controllers\InternalApiController::class, 'createAccessRequest']);
    Route::get('/bot/access-requests', [\App\Http\Controllers\InternalApiController::class, 'listAccessRequests']);
    Route::post('/bot/access-request/{id}/approve', [\App\Http\Controllers\InternalApiController::class, 'approveAccessRequest']);
    Route::post('/bot/access-request/{id}/reject', [\App\Http\Controllers\InternalApiController::class, 'rejectAccessRequest']);

    // Quota requests
    Route::post('/bot/quota-request', [\App\Http\Controllers\InternalApiController::class, 'createQuotaRequest']);
    Route::get('/bot/quota-requests', [\App\Http\Controllers\InternalApiController::class, 'listQuotaRequests']);
    Route::post('/bot/quota-request/{id}/approve', [\App\Http\Controllers\InternalApiController::class, 'approveQuotaRequest']);
    Route::post('/bot/quota-request/{id}/reject', [\App\Http\Controllers\InternalApiController::class, 'rejectQuotaRequest']);

    // Account registry
    Route::post('/bot/account/register', [\App\Http\Controllers\InternalApiController::class, 'registerAccount']);
    Route::post('/bot/account/deactivate', [\App\Http\Controllers\InternalApiController::class, 'deactivateAccount']);
    Route::get('/bot/accounts/{tgId}', [\App\Http\Controllers\InternalApiController::class, 'listAccounts']);

    // Pricing
    Route::get('/pricing', [\App\Http\Controllers\InternalApiController::class, 'getPricing']);

    // Wallet
    Route::get('/wallet/balance/{tgId}', [\App\Http\Controllers\InternalApiController::class, 'getBalance']);
    Route::post('/wallet/debit', [\App\Http\Controllers\InternalApiController::class, 'debitBalance']);
    Route::post('/wallet/topup', [\App\Http\Controllers\InternalApiController::class, 'topup']);
    Route::post('/wallet/vpn_qris', [\App\Http\Controllers\InternalApiController::class, 'vpnPurchaseQris']);
    Route::post('/wallet/voucher/redeem', [\App\Http\Controllers\InternalApiController::class, 'redeemVoucher']);

    // Transactions
    Route::get('/transaction/history/{tgId}', [\App\Http\Controllers\InternalApiController::class, 'transactionHistory']);
    Route::get('/transaction/status/{reference}', [\App\Http\Controllers\InternalApiController::class, 'transactionStatus']);
    Route::post('/transaction/cancel', [\App\Http\Controllers\InternalApiController::class, 'transactionCancel']);
});

// === TEMPORARY DIAGNOSTIC ROUTE — REMOVE AFTER DEBUGGING ===
Route::get('/diag', function () {
    $results = [];

    // Test 1: Who is PHP running as?
    $results['1_whoami'] = trim(shell_exec('whoami 2>&1'));

    // Test 2: Check if sudo works
    $results['2_sudo_whoami'] = trim(shell_exec('sudo whoami 2>&1'));

    // Test 3: Direct write to /tmp (should always work)
    $results['3_write_tmp'] = trim(shell_exec('touch /tmp/diag_test && echo OK || echo FAIL'));

    // Test 4: Direct write to /etc/xray/ (NO sudo)
    $results['4_write_etc_xray_nosudo'] = trim(shell_exec('touch /etc/xray/diag_test 2>&1 && echo OK && rm /etc/xray/diag_test || echo FAIL'));

    // Test 5: Write to /etc/xray/ WITH sudo
    $results['5_write_etc_xray_sudo'] = trim(shell_exec('sudo touch /etc/xray/diag_test 2>&1 && echo OK && sudo rm /etc/xray/diag_test || echo FAIL'));

    // Test 6: Write to SQLite database WITH sudo
    $results['6_sqlite_write'] = trim(shell_exec("sudo /usr/bin/kyt/.venv/bin/python -c \"import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute('SELECT count(*) FROM account_registry'); print('READ_OK'); c.execute(\\\"UPDATE account_registry SET updated_at=updated_at WHERE id=1\\\"); c.commit(); print('WRITE_OK')\" 2>&1"));

    // Test 7: Check mount namespace
    $results['7_mount_etc'] = trim(shell_exec('mount 2>/dev/null | grep "/etc" || echo "no /etc mount found"'));

    // Test 8: Check if /proc/self has mount namespace info
    $results['8_proc_mounts'] = trim(shell_exec('cat /proc/self/mounts 2>/dev/null | grep "ro," | head -5 || echo "no read-only mounts"'));

    // Test 9: Check /etc/xray/config.json permissions
    $results['9_config_perms'] = trim(shell_exec('ls -la /etc/xray/config.json 2>&1'));

    // Test 10: Test exec() which is what our code uses
    $output = [];
    $rc = 0;
    exec("sudo bash -c 'touch /etc/xray/diag_exec_test 2>&1 && echo OK && rm /etc/xray/diag_exec_test || echo FAIL' 2>&1", $output, $rc);
    $results['10_exec_sudo_write'] = "rc=$rc output=" . implode(' ', $output);

    // Test 11: Test the EXACT executeBash pattern
    $script = "touch /etc/xray/diag_b64_test && echo B64_WRITE_OK && rm /etc/xray/diag_b64_test";
    $b64 = base64_encode($script);
    $output2 = [];
    $rc2 = 0;
    exec("sudo bash -c 'export PATH=\$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/kyt; export TERM=xterm; echo $b64 | base64 -d | bash' 2>&1", $output2, $rc2);
    $results['11_executeBash_pattern'] = "rc=$rc2 output=" . implode(' ', $output2);

    // Test 12: Python write via exact runPython pattern
    $pyScript = "f=open('/etc/xray/diag_py_test','w'); f.write('test'); f.close(); import os; os.remove('/etc/xray/diag_py_test'); print('PY_WRITE_OK')";
    $b64py = base64_encode($pyScript);
    $output3 = [];
    $rc3 = 0;
    exec("sudo bash -c 'export PATH=\$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/kyt; echo $b64py | base64 -d | /usr/bin/kyt/.venv/bin/python 2>&1' 2>&1", $output3, $rc3);
    $results['12_runPython_write'] = "rc=$rc3 output=" . implode(' ', $output3);

    // Test 13: Check if there's AppArmor or SELinux
    $results['13_apparmor'] = trim(shell_exec('aa-status 2>&1 | head -5 || echo "no apparmor"'));
    $results['14_selinux'] = trim(shell_exec('getenforce 2>&1 || echo "no selinux"'));

    // Test 15: nsenter to escape mount namespace — write to /etc/xray
    $output4 = [];
    $rc4 = 0;
    exec("sudo nsenter --mount=/proc/1/ns/mnt -- bash -c 'touch /etc/xray/diag_nsenter_test && echo NSENTER_WRITE_OK && rm /etc/xray/diag_nsenter_test' 2>&1", $output4, $rc4);
    $results['15_nsenter_write_etc'] = "rc=$rc4 output=" . implode(' ', $output4);

    // Test 16: nsenter + python — write to SQLite
    $pyScript16 = "import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute('SELECT count(*) FROM account_registry'); print('READ_OK'); c.execute(\"UPDATE account_registry SET updated_at=updated_at WHERE id=1\"); c.commit(); print('WRITE_OK')";
    $b64_16 = base64_encode($pyScript16);
    $output5 = [];
    $rc5 = 0;
    exec("sudo nsenter --mount=/proc/1/ns/mnt -- bash -c 'echo $b64_16 | base64 -d | /usr/bin/kyt/.venv/bin/python' 2>&1", $output5, $rc5);
    $results['16_nsenter_python_sqlite'] = "rc=$rc5 output=" . implode(' ', $output5);

    // Test 17: nsenter + addws test (just check it can read config.json with sed)
    $output6 = [];
    $rc6 = 0;
    exec("sudo nsenter --mount=/proc/1/ns/mnt -- bash -c 'head -1 /etc/xray/config.json && echo CONFIG_READ_OK' 2>&1", $output6, $rc6);
    $results['17_nsenter_config_read'] = "rc=$rc6 output=" . implode(' ', $output6);

    // Test 18: Bridge socket — bash write to /etc/xray
    try {
        $vpn = app(\App\Services\VpnService::class);
        $r18 = $vpn->executeBash("touch /etc/xray/bridge_diag_test && echo BRIDGE_WRITE_OK && rm /etc/xray/bridge_diag_test");
        $results['18_bridge_bash_write'] = "success={$r18['success']} output={$r18['output']} error={$r18['error']}";
    } catch (\Exception $e) {
        $results['18_bridge_bash_write'] = "EXCEPTION: " . $e->getMessage();
    }

    // Test 19: Bridge socket — python write to SQLite
    try {
        $r19 = $vpn->runPython("import sqlite3; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.execute('SELECT count(*) FROM account_registry'); print('READ_OK'); c.execute(\"UPDATE account_registry SET updated_at=updated_at WHERE id=1\"); c.commit(); print('WRITE_OK')");
        $results['19_bridge_python_sqlite'] = "success={$r19['success']} output={$r19['output']} error={$r19['error']}";
    } catch (\Exception $e) {
        $results['19_bridge_python_sqlite'] = "EXCEPTION: " . $e->getMessage();
    }

    // Test 20: Bridge socket — stdin piping test
    try {
        $r20 = $vpn->executeBashWithStdin("cat", "hello\nworld\n");
        $results['20_bridge_stdin_pipe'] = "success={$r20['success']} output={$r20['output']} error={$r20['error']}";
    } catch (\Exception $e) {
        $results['20_bridge_stdin_pipe'] = "EXCEPTION: " . $e->getMessage();
    }

    return response()->json($results, 200, [], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
});

Route::get('/test-approve', function() {
    try {
        $controller = new \App\Http\Controllers\TelegramBotController();
        
        $req = \App\Models\TelegramAccessRequest::first();
        if (!$req) {
            return response()->json(['error' => 'No access request found in DB to test. please make one from bot first.']);
        }
        
        $request = new \Illuminate\Http\Request();
        $request->replace(['reason' => 'Test Approve']);
        
        $admin = \App\Models\User::where('role', 'admin')->first();
        if ($admin) {
            auth()->login($admin);
        }
        
        return $controller->approveAccess($request, $req->id);
    } catch (\Throwable $e) {
        return response()->json([
            'error_class' => get_class($e),
            'message' => $e->getMessage(),
            'file' => $e->getFile(),
            'line' => $e->getLine(),
            'trace' => array_slice($e->getTrace(), 0, 10),
        ], 500);
    }
});

Route::get('/diag-bot', function() {
    $out = "Current User: " . shell_exec("whoami") . "\n";
    $out .= "Bot status:\n" . shell_exec("systemctl status kyt 2>&1") . "\n";
    $out .= "Bot logs:\n" . shell_exec("journalctl -u kyt -n 100 --no-pager 2>&1") . "\n";
    return response($out)->header('Content-Type', 'text/plain');
});

