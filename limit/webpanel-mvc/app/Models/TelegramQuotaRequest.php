<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TelegramQuotaRequest extends Model
{
    protected $fillable = [
        'tg_id', 'reason', 'status',
        'admin_id', 'admin_reason', 'processed_at',
    ];

    protected $casts = [
        'processed_at' => 'datetime',
    ];
}
