<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Voucher extends Model
{
    protected $fillable = [
        'code',
        'type',
        'benefit_value',
        'usage_limit',
        'used_count',
        'is_active',
        'expires_at'
    ];

    protected $casts = [
        'benefit_value' => 'decimal:2',
        'usage_limit' => 'integer',
        'used_count' => 'integer',
        'is_active' => 'boolean',
        'expires_at' => 'datetime'
    ];

    public function usages()
    {
        return $this->hasMany(VoucherUsage::class);
    }
}
