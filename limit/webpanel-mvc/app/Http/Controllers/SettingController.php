<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Setting;
use App\Models\Price;

class SettingController extends Controller
{
    public function index()
    {
        $prices = Price::all()->keyBy('protocol');
        
        $settings = Setting::all()->pluck('value', 'key');
        
        return view('admin.settings', compact('prices', 'settings'));
    }

    public function updatePrices(Request $request)
    {
        $data = $request->validate([
            'prices.*.price' => 'required|numeric|min:0',
        ]);

        foreach ($request->prices as $protocol => $values) {
            Price::updateOrCreate(
                ['protocol' => $protocol],
                ['price' => $values['price'], 'days' => 30] // Default base is 30 days or unit cost
            );
        }

        if ($request->has('extra_ip_price')) {
            Price::updateOrCreate(
                ['protocol' => 'add_ip'],
                ['price' => $request->extra_ip_price, 'days' => null]
            );
        }

        return back()->with('sweet_success', 'Harga layanan berhasil diperbarui!');
    }

    public function updatePayment(Request $request)
    {
        $request->validate([
            'qris_payload' => 'required|string',
            'payment_secret_key' => 'required|string',
        ]);

        Setting::updateOrCreate(['key' => 'qris_payload'], ['value' => $request->qris_payload]);
        Setting::updateOrCreate(['key' => 'payment_secret_key'], ['value' => $request->payment_secret_key]);

        return back()->with('sweet_success', 'Pengaturan pembayaran berhasil diperbarui!');
    }

    public function updateAnnouncement(Request $request)
    {
        $request->validate([
            'login_announcement' => 'required|string',
        ]);

        Setting::updateOrCreate(['key' => 'login_announcement'], ['value' => $request->login_announcement]);

        return back()->with('sweet_success', 'Pengumuman halaman login berhasil diperbarui!');
    }
}
