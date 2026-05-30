<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class VoucherUsage extends Model
{
    const UPDATED_AT = null;

    protected $fillable = [
        'user_id',
        'voucher_id',
        'benefit_type',
        'benefit_amount'
    ];

    protected $casts = [
        'benefit_amount' => 'decimal:2'
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function voucher()
    {
        return $this->belongsTo(Voucher::class);
    }
}
