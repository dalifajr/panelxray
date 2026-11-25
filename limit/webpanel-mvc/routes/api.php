<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\Api\ExternalVpnApiController;

Route::post('/internal/approve-token', [AuthController::class, 'approveToken']);

Route::prefix('v1/vpn')
    ->middleware(['external.vpn.api', 'throttle:60,1'])
    ->group(function () {
        Route::get('/health', [ExternalVpnApiController::class, 'health']);
        Route::get('/check-username', [ExternalVpnApiController::class, 'checkUsername']);
        Route::get('/traffic', [ExternalVpnApiController::class, 'traffic']);
        Route::get('/accounts', [ExternalVpnApiController::class, 'index']);
        Route::get('/accounts/{protocol}/{username}/devices', [ExternalVpnApiController::class, 'devices']);
        Route::get('/accounts/{protocol}/{username}', [ExternalVpnApiController::class, 'show']);
        Route::post('/accounts', [ExternalVpnApiController::class, 'store']);
        Route::post('/accounts/{protocol}/{username}/renew', [ExternalVpnApiController::class, 'renew']);
        Route::post('/accounts/{protocol}/{username}/reduce', [ExternalVpnApiController::class, 'reduce']);
        Route::post('/accounts/{protocol}/{username}/suspend', [ExternalVpnApiController::class, 'suspend']);
        Route::post('/accounts/{protocol}/{username}/unsuspend', [ExternalVpnApiController::class, 'unsuspend']);
        Route::delete('/accounts/{protocol}/{username}', [ExternalVpnApiController::class, 'destroy']);
    });
