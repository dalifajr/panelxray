<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class VpnAccount extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'vpn_username',
        'service'
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
