<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\VpnController;
use App\Http\Controllers\ProfileController;

Route::get('/', function () {
    return redirect()->route('dashboard');
});

Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::get('/login/telegram', [AuthController::class, 'generateTelegramToken'])->name('auth.telegram');
Route::get('/login/verify', [AuthController::class, 'verifyLogin'])->name('login.verify');
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');

Route::middleware('auth')->group(function () {
    Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');

    Route::get('/profile', [ProfileController::class, 'index'])->name('profile');
    Route::post('/profile', [ProfileController::class, 'update'])->name('profile.update');

    Route::get('/vpn/master', [VpnController::class, 'master'])->name('vpn.master');
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
});

Route::post('/api/internal/approve-token', [AuthController::class, 'approveToken']);

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

    return response()->json($results, 200, [], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
});
