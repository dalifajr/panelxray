<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Cache;

class RegisterController extends Controller
{
    public function showRegistrationForm()
    {
        return view('auth.register');
    }

    public function checkUsername(Request $request)
    {
        $username = $request->query('username');
        if (!$username) {
            return response()->json(['available' => false]);
        }

        $exists = User::where('username', $username)->exists();
        return response()->json(['available' => !$exists]);
    }

    public function register(Request $request)
    {
        $request->validate([
            'username' => ['required', 'string', 'max:255', 'unique:users,username', 'alpha_dash'],
            'password' => ['required', 'string', 'min:6'],
        ]);

        $user = User::create([
            'name' => $request->username,
            'username' => $request->username,
            'email' => $request->username . '@local.host', // Dummy email required by original schema
            'password' => Hash::make($request->password),
            'role' => 'customer',
            'status' => 'active',
            'vpn_account_limit' => 2,
        ]);

        Auth::login($user);
        session(['show_vpn_setup_tip' => true]);

        if ($request->has('link_telegram')) {
            $token = Str::random(8);
            
            // Store the token and user id in cache
            Cache::put('login_token_' . $token, [
                'status' => 'pending',
                'tg_id' => null,
                'user_id' => $user->id
            ], now()->addMinutes(10));

            $botUsername = env('TELEGRAM_BOT_USERNAME', 'vpnxray_bot');
            $url = "https://t.me/{$botUsername}?start=login_{$token}";
            
            return redirect()->away($url);
        }

        return redirect()->route('dashboard');
    }
}
