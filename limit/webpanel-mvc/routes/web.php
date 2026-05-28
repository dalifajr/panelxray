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
