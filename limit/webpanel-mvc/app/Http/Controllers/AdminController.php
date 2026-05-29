<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;

class AdminController extends Controller
{
    public function users()
    {
        // Must be admin
        if (auth()->user()->role !== 'admin') {
            abort(403);
        }

        $users = User::withCount('vpnAccounts')->get();
        return view('admin.users', compact('users'));
    }

    public function updateUser(Request $request, User $user)
    {
        if (auth()->user()->role !== 'admin') {
            abort(403);
        }

        $validated = $request->validate([
            'role' => 'required|in:admin,customer',
            'status' => 'required|in:active,suspended',
            'vpn_account_limit' => 'required|integer|min:0',
        ]);

        $user->update($validated);

        return back()->with('sweet_success', 'Data user berhasil diperbarui.');
    }

    public function deleteUser(User $user)
    {
        if (auth()->user()->role !== 'admin') {
            abort(403);
        }

        if ($user->id === auth()->id()) {
            return back()->with('sweet_error', 'Anda tidak dapat menghapus akun Anda sendiri.');
        }

        $user->delete();

        return back()->with('sweet_success', 'User berhasil dihapus.');
    }
}
