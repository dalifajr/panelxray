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
            'max_ip_limit' => 'nullable|integer|min:0',
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

        if ($request->has('max_ip_limit')) {
            Setting::updateOrCreate(
                ['key' => 'max_ip_limit'],
                ['value' => $request->max_ip_limit]
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

        // Sync to .env
        $this->setEnvValue('PAYMENT_SECRET_KEY', $request->payment_secret_key);

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

    public function updateBotSettings(Request $request)
    {
        $request->validate([
            'bot_mode' => 'required|in:admin_only,sales',
            'bot_trial_enabled' => 'nullable|string',
            'bot_trial_days' => 'required|integer|min:1',
            'bot_default_ssh_limit' => 'required|integer|min:0',
            'bot_default_xray_limit' => 'required|integer|min:0',
        ]);

        Setting::updateOrCreate(['key' => 'bot_mode'], ['value' => $request->bot_mode]);
        Setting::updateOrCreate(
            ['key' => 'bot_trial_enabled'],
            ['value' => $request->has('bot_trial_enabled') ? 'true' : 'false']
        );
        Setting::updateOrCreate(['key' => 'bot_trial_days'], ['value' => $request->bot_trial_days]);
        Setting::updateOrCreate(['key' => 'bot_default_ssh_limit'], ['value' => $request->bot_default_ssh_limit]);
        Setting::updateOrCreate(['key' => 'bot_default_xray_limit'], ['value' => $request->bot_default_xray_limit]);

        // Sync to .env
        $this->setEnvValue('BOT_MODE', $request->bot_mode);
        $this->setEnvValue('BOT_TRIAL_ENABLED', $request->has('bot_trial_enabled') ? 'true' : 'false');
        $this->setEnvValue('BOT_TRIAL_DAYS', $request->bot_trial_days);

        // Restart bot service to apply settings if bot is active
        try {
            $vpnService = app(\App\Services\VpnService::class);
            $vpnService->executeBash("systemctl restart kyt");
        } catch (\Exception $e) {
            // Ignore if service command fails
        }

        return back()->with('sweet_success', 'Pengaturan bot Telegram berhasil diperbarui!');
    }

    private function setEnvValue($key, $value)
    {
        $path = base_path('.env');
        if (file_exists($path)) {
            $content = file_get_contents($path);
            
            // Normalize value (escape quotes if any)
            $escaped = str_replace('"', '\\"', $value);
            
            if (preg_match("/^{$key}=/m", $content)) {
                $content = preg_replace("/^{$key}=.*/m", "{$key}=\"{$escaped}\"", $content);
            } else {
                $content .= "\n{$key}=\"{$escaped}\"\n";
            }
            file_put_contents($path, $content);
        }
    }
}
