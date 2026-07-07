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
}
