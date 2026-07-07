<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TelegramAccountRegistry extends Model
{
    protected $table = 'telegram_account_registry';

    protected $fillable = [
        'tg_id', 'service', 'category', 'username',
        'expires_at', 'is_trial', 'active',
    ];

    protected $casts = [
        'is_trial' => 'boolean',
        'active' => 'boolean',
    ];
}
