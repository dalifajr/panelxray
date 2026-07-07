<?php

namespace App\Http\Controllers;

use App\Models\User;
use App\Models\TelegramBotUser;
use App\Models\TelegramAccessRequest;
use App\Models\TelegramQuotaRequest;
use Illuminate\Http\Request;

class TelegramBotController extends Controller
{
    public function index()
    {
        $botUsers = TelegramBotUser::with('webUser')->orderBy('created_at', 'desc')->get();
        $accessRequests = TelegramAccessRequest::where('status', 'pending')->orderBy('created_at', 'desc')->get();
        $quotaRequests = TelegramQuotaRequest::where('status', 'pending')->orderBy('created_at', 'desc')->get();
        $webUsers = User::orderBy('name', 'asc')->get();

        return view('admin.telegram-users', compact('botUsers', 'accessRequests', 'quotaRequests', 'webUsers'));
    }

    public function updateUser(Request $request, TelegramBotUser $botUser)
    {
        $validated = $request->validate([
            'role' => 'required|in:admin,reseller,user',
            'status' => 'required|in:pending,approved,rejected,suspended',
            'ssh_limit' => 'required|integer|min:0',
            'xray_limit' => 'required|integer|min:0',
            'user_id' => 'nullable|exists:users,id',
            'note' => 'nullable|string|max:255',
        ]);

        $botUser->update($validated);

        return back()->with('sweet_success', 'Data user bot Telegram berhasil diperbarui!');
    }

    public function deleteUser(TelegramBotUser $botUser)
    {
        $botUser->delete();
        return back()->with('sweet_success', 'User bot Telegram berhasil dihapus!');
    }

    public function approveAccess(Request $request, int $id)
    {
        $req = TelegramAccessRequest::findOrFail($id);
        
        $botUser = TelegramBotUser::firstOrCreate(
            ['tg_id' => $req->tg_id],
            [
                'tg_username' => $req->tg_username,
                'tg_full_name' => $req->tg_full_name,
                'role' => 'user',
                'status' => 'approved',
            ]
        );

        $botUser->status = 'approved';
        $botUser->save();

        $req->update([
            'status' => 'approved',
            'admin_id' => (string)auth()->id(),
            'admin_reason' => $request->input('reason', 'Approved via Web Admin'),
            'processed_at' => now(),
        ]);

        return back()->with('sweet_success', 'Request akses berhasil disetujui!');
    }

    public function rejectAccess(Request $request, int $id)
    {
        $req = TelegramAccessRequest::findOrFail($id);

        $botUser = TelegramBotUser::where('tg_id', $req->tg_id)->first();
        if ($botUser) {
            $botUser->status = 'rejected';
            $botUser->save();
        }

        $req->update([
            'status' => 'rejected',
            'admin_id' => (string)auth()->id(),
            'admin_reason' => $request->input('reason', 'Rejected via Web Admin'),
            'processed_at' => now(),
        ]);

        return back()->with('sweet_success', 'Request akses berhasil ditolak.');
    }

    public function approveQuota(Request $request, int $id)
    {
        $req = TelegramQuotaRequest::findOrFail($id);

        $botUser = TelegramBotUser::where('tg_id', $req->tg_id)->first();
        if (!$botUser) {
            return back()->with('sweet_error', 'User bot Telegram tidak ditemukan!');
        }

        $sshAdd = (int)$request->input('ssh_add', 0);
        $xrayAdd = (int)$request->input('xray_add', 0);

        $botUser->ssh_limit += $sshAdd;
        $botUser->xray_limit += $xrayAdd;
        $botUser->save();

        $req->update([
            'status' => 'approved',
            'admin_id' => (string)auth()->id(),
            'admin_reason' => $request->input('reason', "Approved: SSH +{$sshAdd}, Xray +{$xrayAdd}"),
            'processed_at' => now(),
        ]);

        return back()->with('sweet_success', 'Request kuota berhasil disetujui!');
    }

    public function rejectQuota(Request $request, int $id)
    {
        $req = TelegramQuotaRequest::findOrFail($id);

        $req->update([
            'status' => 'rejected',
            'admin_id' => (string)auth()->id(),
            'admin_reason' => $request->input('reason', 'Rejected via Web Admin'),
            'processed_at' => now(),
        ]);

        return back()->with('sweet_success', 'Request kuota berhasil ditolak.');
    }
}
