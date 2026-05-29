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

        if ($user->id === auth()->id()) {
            return back()->with('sweet_error', 'Anda tidak dapat mengubah status atau peran akun Anda sendiri dari halaman ini.');
        }

        $validated = $request->validate([
            'role' => 'required|in:admin,customer',
            'status' => 'required|in:active,suspended',
            'vpn_account_limit' => 'required|integer|min:0',
        ]);

        $status_changed = $user->status !== $validated['status'];
        $user->update($validated);

        if ($status_changed) {
            $vpnService = app(\App\Services\VpnService::class);
            foreach ($user->vpnAccounts as $acc) {
                $protocol = $acc->service;
                $userStr = $acc->vpn_username;
                if ($validated['status'] === 'suspended') {
                    if ($protocol === 'ssh') {
                        $vpnService->executeBash("usermod -L $userStr");
                    } else {
                        $scriptMap = ['vmess' => 'suspws', 'vless' => 'suspvless', 'trojan' => 'susptr', 'shadowsocks' => 'suspss'];
                        $cmd = $scriptMap[$protocol] ?? 'suspws';
                        $vpnService->executeBash("$cmd --user $userStr --reason manual");
                    }
                    $acc->admin_suspended = true;
                    $acc->save();
                } else {
                    if ($protocol === 'ssh') {
                        $vpnService->executeBash("usermod -U $userStr");
                    } else {
                        $scriptMap = ['vmess' => 'unsuspws', 'vless' => 'unsuspvless', 'trojan' => 'unsusptr', 'shadowsocks' => 'unsuspss'];
                        $cmd = $scriptMap[$protocol] ?? 'unsuspws';
                        $vpnService->executeBash("$cmd --user $userStr");
                    }
                    $acc->admin_suspended = false;
                    $acc->save();
                }
            }
        }

        return back()->with('sweet_success', 'Data user berhasil diperbarui.');
    }

    public function resetPassword(Request $request, User $user)
    {
        if (auth()->user()->role !== 'admin') {
            abort(403);
        }

        $validated = $request->validate([
            'new_password' => 'required|string|min:6',
        ]);

        $user->password = bcrypt($validated['new_password']);
        $user->save();

        return back()->with('sweet_success', "Password untuk user {$user->username} berhasil direset.");
    }

    public function unlinkTelegram(User $user)
    {
        if (auth()->user()->role !== 'admin') {
            abort(403);
        }

        $user->telegram_id = null;
        $user->save();

        return back()->with('sweet_success', "Tautan Telegram untuk user {$user->username} berhasil dilepas.");
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

    public function injectBalance(Request $request, User $user)
    {
        $request->validate([
            'amount' => 'required|numeric|min:1'
        ]);

        $user->balance += $request->amount;
        $user->save();

        \App\Models\Transaction::create([
            'reference' => 'INJ-' . strtoupper(\Illuminate\Support\Str::random(10)),
            'user_id' => $user->id,
            'type' => 'topup',
            'amount' => $request->amount,
            'unique_code' => 0,
            'total_amount' => $request->amount,
            'status' => 'success',
            'description' => 'Saldo diinjeksi oleh Admin',
        ]);

        \App\Models\Notification::create([
            'user_id' => $user->id,
            'type' => 'system',
            'message' => 'Admin telah menambahkan saldo sebesar Rp ' . number_format($request->amount, 0, ',', '.') . ' ke dompet Anda.',
        ]);

        return back()->with('sweet_success', 'Saldo berhasil diinjeksi!');
    }

    public function blockBalance(Request $request, User $user)
    {
        $oldBalance = $user->balance;
        $user->balance = 0;
        $user->save();

        \App\Models\Notification::create([
            'user_id' => $user->id,
            'type' => 'system',
            'message' => 'Saldo Anda (Rp ' . number_format($oldBalance, 0, ',', '.') . ') telah diblokir/dihapus oleh Admin.',
        ]);

        return back()->with('sweet_success', 'Saldo user berhasil di-nol-kan!');
    }
}
