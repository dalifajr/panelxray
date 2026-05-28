<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\VpnController;

Route::get('/', function () {
    return redirect()->route('login');
});

Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::get('/login/verify', [AuthController::class, 'verifyLogin'])->name('login.verify');
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');

Route::middleware('auth')->group(function () {
    Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');

    // VPN Management Routes
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
