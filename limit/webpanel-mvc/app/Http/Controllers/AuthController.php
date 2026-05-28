<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Str;
use App\Models\User;

class AuthController extends Controller
{
    public function showLogin()
    {
        if (Auth::check()) {
            return redirect()->route('dashboard');
        }
        return view('auth.login');
    }

    public function generateTelegramToken()
    {
        $token = Str::random(8);
        
        // Store in cache for 10 minutes as pending
        Cache::put('login_token_' . $token, [
            'status' => 'pending',
            'tg_id' => null
        ], now()->addMinutes(10));

        // Redirect to Telegram Bot with the token
        // E.g., https://t.me/YourBotName?start=login_token
        // Ideally we fetch the bot username from .env
        $botUsername = env('TELEGRAM_BOT_USERNAME', 'vpnxray_bot');
        $url = "https://t.me/{$botUsername}?start=login_{$token}";
        
        return redirect()->away($url);
    }

    // This is called internally by the Python Bot
    public function approveToken(Request $request)
    {
        // Simple security check (could use an internal secret key)
        if ($request->header('X-Internal-Secret') !== env('INTERNAL_API_SECRET', 'secret123')) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $token = $request->input('token');
        $tgId = $request->input('tg_id');

        $cacheKey = 'login_token_' . $token;
        if (!Cache::has($cacheKey)) {
            return response()->json(['error' => 'Token expired or invalid'], 404);
        }

        Cache::put($cacheKey, [
            'status' => 'approved',
            'tg_id' => $tgId
        ], now()->addMinutes(10));

        return response()->json(['success' => true]);
    }

    public function verifyLogin(Request $request)
    {
        $token = $request->input('token');
        $cacheKey = 'login_token_' . $token;

        $tokenData = Cache::get($cacheKey);

        if (!$tokenData) {
            return redirect()->route('login')->with('error', 'Token login tidak valid atau sudah kadaluarsa.');
        }

        if ($tokenData['status'] !== 'approved') {
            return redirect()->route('login')->with('error', 'Token belum diotorisasi oleh bot.');
        }

        // Login the user (Create dummy user on the fly if needed, or find by tg_id)
        $user = User::firstOrCreate(
            ['email' => $tokenData['tg_id'] . '@telegram.local'],
            [
                'name' => 'Admin ' . $tokenData['tg_id'],
                'password' => bcrypt(Str::random(16)),
            ]
        );
        $user->tg_id = $tokenData['tg_id'];
        $user->save();

        Auth::login($user);
        
        // Clear token
        Cache::forget($cacheKey);

        return redirect()->route('dashboard');
    }

    public function logout()
    {
        Auth::logout();
        return redirect()->route('login');
    }
}
