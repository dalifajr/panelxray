<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TelegramAccessRequest extends Model
{
    protected $fillable = [
        'tg_id', 'tg_username', 'tg_full_name', 'reason',
        'status', 'admin_id', 'admin_reason', 'processed_at',
    ];

    protected $casts = [
        'processed_at' => 'datetime',
    ];
}
