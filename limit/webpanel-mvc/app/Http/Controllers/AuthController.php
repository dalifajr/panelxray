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

    public function login(Request $request)
    {
        $credentials = $request->validate([
            'username' => ['required', 'string'],
            'password' => ['required', 'string'],
        ]);

        if (Auth::attempt($credentials)) {
            $request->session()->regenerate();

            if (Auth::user()->status === 'suspended') {
                Auth::logout();
                $request->session()->invalidate();
                $request->session()->regenerateToken();
                return back()->with('error', 'Akun Anda telah disuspend oleh Administrator.');
            }

            return redirect()->route('dashboard');
        }

        return back()->with('error', 'Username atau Password salah.')->onlyInput('username');
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

        // Fetch user info from Bot's SQLite database via VpnService
        $vpn = app(\App\Services\VpnService::class);
        $script = "import sqlite3, json; c=sqlite3.connect('/usr/bin/kyt/database.db'); c.row_factory=sqlite3.Row; r=c.execute('SELECT username, full_name FROM telegram_users WHERE tg_id = ?', ('{$tokenData['tg_id']}',)).fetchone(); print(json.dumps(dict(r) if r else {}))";
        $res = $vpn->execute('/usr/bin/kyt/.venv/bin/python', ['-c', $script]);
        
        $fullName = 'User Panel';
        if ($res['success']) {
            $botUser = json_decode($res['output'], true);
            if (!empty($botUser['full_name'])) {
                $fullName = $botUser['full_name'];
            } elseif (!empty($botUser['username'])) {
                $fullName = $botUser['username'];
            }
        }

        if (isset($tokenData['user_id'])) {
            // Ini adalah token dari proses pendaftaran untuk menautkan Telegram
            $user = User::find($tokenData['user_id']);
            if ($user) {
                $user->telegram_id = $tokenData['tg_id'];
                $user->save();
            }
            Auth::login($user);
        } else {
            // Login langsung menggunakan Telegram
            $user = User::where('telegram_id', $tokenData['tg_id'])
                        ->orWhere('email', $tokenData['tg_id'] . '@telegram.local')
                        ->first();
            
            if (!$user) {
                // Buat user baru otomatis
                $isFirstUser = User::count() === 0;
                $user = User::create([
                    'name' => $fullName,
                    'username' => null,
                    'email' => $tokenData['tg_id'] . '@telegram.local',
                    'password' => bcrypt(Str::random(24)),
                    'role' => $isFirstUser ? 'admin' : 'customer',
                    'telegram_id' => $tokenData['tg_id']
                ]);
            } else {
                if (empty($user->telegram_id)) {
                    $user->telegram_id = $tokenData['tg_id'];
                }
                if ($user->name === 'Admin Panel' && $fullName !== 'Admin Panel') {
                    $user->name = $fullName;
                }
                $user->save();
            }

            if ($user->status === 'suspended') {
                Cache::forget($cacheKey);
                return redirect()->route('login')->with('error', 'Akun Anda telah disuspend oleh Administrator.');
            }

            Auth::login($user);
        }
        
        // Clear token
        Cache::forget($cacheKey);

        return redirect()->route('dashboard');
    }

    public function logout(Request $request)
    {
        Auth::logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();
        return redirect()->route('login');
    }
}
