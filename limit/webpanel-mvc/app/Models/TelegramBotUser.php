<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TelegramBotUser extends Model
{
    protected $fillable = [
        'tg_id',
        'tg_username',
        'tg_full_name',
        'role',
        'status',
        'note',
        'ssh_limit',
        'xray_limit',
        'user_id',
    ];

    public function webUser()
    {
        return $this->belongsTo(User::class, 'user_id');
    }

    public function isAdmin(): bool
    {
        return $this->role === 'admin' && $this->status === 'approved';
    }

    public function isApproved(): bool
    {
        return $this->status === 'approved';
    }

    public function accessRequests()
    {
        return $this->hasMany(TelegramAccessRequest::class, 'tg_id', 'tg_id');
    }

    public function quotaRequests()
    {
        return $this->hasMany(TelegramQuotaRequest::class, 'tg_id', 'tg_id');
    }

    public function accountRegistry()
    {
        return $this->hasMany(TelegramAccountRegistry::class, 'tg_id', 'tg_id');
    }

    public function syncWebUser()
    {
        if ($this->status !== 'approved') {
            return null;
        }

        $webUser = User::where('telegram_id', $this->tg_id)
            ->orWhere('email', $this->tg_id . '@telegram.local')
            ->first();

        if (!$webUser) {
            $username = $this->tg_username ?: 'tg_' . $this->tg_id;
            
            $originalUsername = $username;
            $counter = 1;
            while (User::where('username', $username)->exists()) {
                $username = $originalUsername . '_' . $counter;
                $counter++;
            }

            $fullName = $this->tg_full_name ?: ($this->tg_username ?: 'Telegram User ' . $this->tg_id);

            $webUser = User::create([
                'name' => $fullName,
                'username' => $username,
                'email' => $this->tg_id . '@telegram.local',
                'password' => bcrypt(\Illuminate\Support\Str::random(24)),
                'role' => 'customer',
                'status' => 'active',
                'telegram_id' => $this->tg_id,
                'vpn_account_limit' => 2,
            ]);
        }

        if (empty($this->user_id) || $this->user_id != $webUser->id) {
            $this->user_id = $webUser->id;
            $this->save();
        }

        return $webUser;
    }
}
