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

        if (env('TURNSTILE_SECRET_KEY') && env('TURNSTILE_SITE_KEY')) {
            $token = $request->input('cf-turnstile-response');
            if (!$token) {
                return back()->withErrors(['captcha' => 'Silakan selesaikan Cloudflare Captcha.'])->withInput();
            }
            
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, "https://challenges.cloudflare.com/turnstile/v0/siteverify");
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
                'secret' => env('TURNSTILE_SECRET_KEY'),
                'response' => $token,
                'remoteip' => $request->ip()
            ]));
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);
            curl_close($ch);
            
            $res = json_decode($response, true);
            if (!($res['success'] ?? false)) {
                return back()->withErrors(['captcha' => 'Verifikasi keamanan Cloudflare Captcha gagal. Silakan coba lagi.'])->withInput();
            }
        }

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
