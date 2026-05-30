<?php

namespace App\Http\Controllers;

use App\Models\Voucher;
use Illuminate\Http\Request;

class VoucherController extends Controller
{
    public function index()
    {
        $vouchers = Voucher::withCount('usages')->orderBy('created_at', 'desc')->get();
        return view('admin.vouchers', compact('vouchers'));
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'code' => 'required|string|unique:vouchers,code|max:30|regex:/^[a-zA-Z0-9_-]+$/',
            'type' => 'required|in:free_balance,double_saldo',
            'benefit_value' => 'required|numeric|min:0',
            'usage_limit' => 'required|integer|min:1',
            'expires_at' => 'nullable|date|after:today',
        ]);

        $validated['code'] = strtoupper($validated['code']);

        Voucher::create([
            'code' => $validated['code'],
            'type' => $validated['type'],
            'benefit_value' => $validated['benefit_value'],
            'usage_limit' => $validated['usage_limit'],
            'is_active' => true,
            'expires_at' => $validated['expires_at'] ? \Carbon\Carbon::parse($validated['expires_at'])->endOfDay() : null,
        ]);

        return back()->with('sweet_success', 'Voucher baru berhasil dibuat!');
    }

    public function destroy(Voucher $voucher)
    {
        $voucher->delete();
        return back()->with('sweet_success', 'Voucher berhasil dihapus!');
    }
}
