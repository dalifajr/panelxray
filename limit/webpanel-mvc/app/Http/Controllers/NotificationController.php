<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\Notification;
use App\Models\User;

class NotificationController extends Controller
{
    public function index()
    {
        $notifications = Auth::user()->notifications()->orderBy('created_at', 'desc')->paginate(15);
        return view('notifications.index', compact('notifications'));
    }

    public function readAll()
    {
        Auth::user()->notifications()->where('is_read', false)->update(['is_read' => true]);
        return back()->with('sweet_success', 'Semua notifikasi telah ditandai dibaca.');
    }

    public function broadcast(Request $request)
    {
        $request->validate([
            'message' => 'required|string',
        ]);

        $users = User::where('role', 'customer')->get();
        $notifications = [];
        $now = now();
        
        foreach ($users as $user) {
            $notifications[] = [
                'user_id' => $user->id,
                'type' => 'broadcast',
                'message' => $request->message,
                'is_read' => false,
                'created_at' => $now,
                'updated_at' => $now,
            ];
        }

        Notification::insert($notifications);

        return back()->with('sweet_success', 'Pengumuman berhasil disiarkan ke semua customer.');
    }
}
