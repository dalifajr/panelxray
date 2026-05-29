<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\User;

class ProfileController extends Controller
{
    public function index()
    {
        $user = Auth::user();
        return view('profile', compact('user'));
    }

    public function update(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:50',
            'password' => 'nullable|string|min:6',
        ]);

        $user = Auth::user();
        
        // Ensure user is instance of User
        if ($user instanceof User) {
            $user->name = $request->name;
            if ($request->filled('password')) {
                $user->password = bcrypt($request->password);
            }
            $user->save();
            return back()->with('sweet_success', 'Profil berhasil diperbarui!');
        }
        
        return back()->with('sweet_error', 'Gagal memperbarui profil.');
    }

    public function unlinkTelegram()
    {
        $user = Auth::user();
        if ($user instanceof User) {
            $user->telegram_id = null;
            $user->save();
            return back()->with('sweet_success', 'Akun Telegram berhasil dilepas tautannya.');
        }
        return back()->with('sweet_error', 'Gagal melepas tautan Telegram.');
    }
}
