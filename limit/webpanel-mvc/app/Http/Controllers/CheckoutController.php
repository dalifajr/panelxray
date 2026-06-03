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
            ->firstOrFail();

        $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
        $protocol = $meta['protocol'] ?? 'vmess';

        if ($transaction->status === 'success') {
            return redirect()->route('checkout.success', $id);
        } elseif ($transaction->status === 'cancelled') {
            return redirect()->route('checkout.cancelled', $id);
        } elseif ($transaction->status !== 'pending') {
            return redirect()->route('vpn.index', $protocol)->with('sweet_error', 'Status transaksi tidak valid.');
        }

        // Check if 5 minutes expired for pending transactions
        if ($transaction->created_at->addMinutes(5)->isPast()) {
            $transaction->status = 'cancelled';
            $transaction->save();
            return redirect()->route('checkout.cancelled', $id);
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
        $transaction->update(['status' => 'cancelled']);

        return redirect()->route('checkout.cancelled', $id);
    }
    
    public function success($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->whereIn('type', ['vpn_purchase_qris', 'vpn_renew_qris'])
            ->where('status', 'success')
            ->firstOrFail();
            
        $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
        
        return view('customer.payment-success', compact('transaction', 'meta'));
    }
    
    public function cancelled($id)
    {
        $transaction = Transaction::where('id', $id)
            ->where('user_id', auth()->id())
            ->whereIn('type', ['vpn_purchase_qris', 'vpn_renew_qris'])
            ->where('status', 'cancelled')
            ->firstOrFail();
            
        $meta = is_string($transaction->metadata) ? json_decode($transaction->metadata, true) : $transaction->metadata;
        $reason = $meta['cancel_reason'] ?? 'Dibatalkan oleh user atau waktu pembayaran habis.';
        
        return view('customer.payment-cancelled', compact('transaction', 'meta', 'reason'));
    }
}
