<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Transaction;
use App\Helpers\QrisHelper;
use Carbon\Carbon;

class CheckoutController extends Controller
{
    public function show($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->whereIn('type', ['vpn_purchase_qris', 'vpn_renew_qris'])
            ->where('status', 'pending')
            ->firstOrFail();

        // Check if 5 minutes expired
        if (Carbon::now()->diffInMinutes($transaction->created_at) >= 5) {
            $transaction->update(['status' => 'cancelled']);
            $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
            $protocol = $meta['protocol'] ?? 'vmess';
            return redirect()->route('vpn.index', $protocol)->with('sweet_error', 'Waktu pembayaran telah habis. Pesanan dibatalkan.');
        }

        $settings = \App\Models\Setting::pluck('value', 'key')->toArray();
        $qrisPayload = $settings['qris_payload'] ?? null;
        
        $dynamicQris = null;
        if ($qrisPayload) {
            $dynamicQris = QrisHelper::generateDynamic($qrisPayload, $transaction->total_amount);
        }

        return view('customer.checkout', compact('transaction', 'dynamicQris'));
    }

    public function cancel($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->whereIn('type', ['vpn_purchase_qris', 'vpn_renew_qris'])
            ->where('status', 'pending')
            ->firstOrFail();

        $transaction->update(['status' => 'cancelled']);
        $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
        $protocol = $meta['protocol'] ?? 'vmess';
        return redirect()->route('vpn.index', $protocol)->with('sweet_success', 'Pesanan berhasil dibatalkan.');
    }
}
