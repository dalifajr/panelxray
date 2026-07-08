<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use App\Models\Setting;
use App\Models\Price;
use App\Models\User;
use App\Models\Transaction;
use App\Models\TelegramBotUser;
use App\Models\TelegramAccessRequest;
use App\Models\TelegramQuotaRequest;
use App\Models\TelegramAccountRegistry;
use Illuminate\Support\Facades\Log;
use Carbon\Carbon;

class InternalApiController extends Controller
{
    /**
     * Validate X-Internal-Secret header against stored payment_secret_key.
     */
    private function authorize(Request $request): bool
    {
        $secret = $request->header('X-Internal-Secret');
        if (!$secret) {
            \Illuminate\Support\Facades\Log::warning("Internal API Auth Failed: Missing X-Internal-Secret header.");
            return false;
        }
        $storedKey = Setting::where('key', 'payment_secret_key')->value('value');
        if (empty($storedKey)) {
            $ok = ($secret === 'secret123');
            if (!$ok) {
                \Illuminate\Support\Facades\Log::warning("Internal API Auth Failed: Fallback key mismatch. Received: '{$secret}'");
            }
            return $ok;
        }
        $ok = hash_equals($storedKey, $secret);
        if (!$ok) {
            \Illuminate\Support\Facades\Log::warning("Internal API Auth Failed: Key mismatch. Stored: '{$storedKey}', Received: '{$secret}'");
        }
        return $ok;
    }

    private function unauthorized(): JsonResponse
    {
        return response()->json(['error' => 'Unauthorized'], 401);
    }

    // ─────────────────────────────────────────────
    // Bot Configuration
    // ─────────────────────────────────────────────

    /**
     * GET /api/internal/bot/config
     * Returns bot mode, trial settings, and other config.
     */
    public function botConfig(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $settings = Setting::all()->pluck('value', 'key');

        return response()->json([
            'bot_mode' => $settings['bot_mode'] ?? 'admin_only',
            'bot_trial_enabled' => ($settings['bot_trial_enabled'] ?? 'false') === 'true',
            'bot_trial_days' => (int)($settings['bot_trial_days'] ?? 1),
            'qris_payload' => $settings['qris_payload'] ?? '',
        ]);
    }

    // ─────────────────────────────────────────────
    // User Management
    // ─────────────────────────────────────────────

    /**
     * POST /api/internal/bot/user/touch
     * Upsert a Telegram user (called every time a user sends a message).
     */
    public function touchUser(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        try {
            $request->validate([
                'tg_id' => 'required|string',
                'tg_username' => 'nullable|string',
                'tg_full_name' => 'nullable|string',
            ]);

            $tgId = $request->input('tg_id');
            $user = TelegramBotUser::where('tg_id', $tgId)->first();

            $botMode = env('BOT_MODE') ?: Setting::where('key', 'bot_mode')->value('value') ?: 'admin_only';
            $status = ($botMode === 'sales') ? 'approved' : 'pending';

            if (!$user) {
                $user = TelegramBotUser::create([
                    'tg_id' => $tgId,
                    'tg_username' => $request->input('tg_username') ?: '',
                    'tg_full_name' => $request->input('tg_full_name') ?: '',
                    'role' => 'user',
                    'status' => $status,
                ]);

                // Try to auto-link if a web panel user has this telegram_id
                $webUser = User::where('telegram_id', $tgId)->first();
                if ($webUser) {
                    $user->user_id = $webUser->id;
                    $user->save();
                }

                if ($status === 'approved') {
                    $user->syncWebUser();
                }
            } else {
                if ($user->status === 'pending' && $botMode === 'sales') {
                    $user->status = 'approved';
                    $user->save();
                    $user->syncWebUser();
                }

                // Update username/full_name if provided
                $changed = false;
                if ($request->filled('tg_username') && $request->input('tg_username') !== $user->tg_username) {
                    $user->tg_username = $request->input('tg_username') ?: '';
                    $changed = true;
                }
                if ($request->filled('tg_full_name') && $request->input('tg_full_name') !== $user->tg_full_name) {
                    $user->tg_full_name = $request->input('tg_full_name') ?: '';
                    $changed = true;
                }
                if ($changed) {
                    $user->save();
                }
            }

            return response()->json(['status' => 'ok', 'user' => $user->fresh()]);
        } catch (\Exception $e) {
            Log::error("touchUser API Exception: " . $e->getMessage() . "\n" . $e->getTraceAsString());
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    /**
     * GET /api/internal/bot/user/{tg_id}
     * Get a specific Telegram user record.
     */
    public function getUser(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        return response()->json(['user' => $user]);
    }

    /**
     * GET /api/internal/bot/user/{tg_id}/status
     * Check if user is approved/admin/pending etc.
     */
    public function getUserStatus(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json([
                'exists' => false,
                'status' => 'unknown',
                'role' => 'user',
                'is_admin' => false,
                'is_approved' => false,
            ]);
        }

        return response()->json([
            'exists' => true,
            'status' => $user->status,
            'role' => $user->role,
            'is_admin' => $user->isAdmin(),
            'is_approved' => $user->isApproved(),
            'note' => $user->note,
        ]);
    }

    /**
     * GET /api/internal/bot/users
     * List all Telegram bot users (admin use).
     */
    public function listUsers(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $status = $request->query('status');
        $query = TelegramBotUser::orderBy('created_at', 'desc');
        if ($status) {
            $query->where('status', $status);
        }

        return response()->json(['users' => $query->get()]);
    }

    /**
     * POST /api/internal/bot/user/{tg_id}/approve
     */
    public function approveUser(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $user->status = 'approved';
        $user->note = $request->input('note', $user->note);
        $user->save();

        // Auto-create and sync web user account
        $user->syncWebUser();

        // Delete related access request
        TelegramAccessRequest::where('tg_id', $tgId)->delete();

        return response()->json(['status' => 'ok', 'user' => $user->fresh()]);
    }

    /**
     * POST /api/internal/bot/user/{tg_id}/reject
     */
    public function rejectUser(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $user->status = 'rejected';
        $user->note = $request->input('note', $user->note);
        $user->save();

        // Delete related access request
        TelegramAccessRequest::where('tg_id', $tgId)->delete();

        return response()->json(['status' => 'ok', 'user' => $user->fresh()]);
    }

    /**
     * POST /api/internal/bot/user/{tg_id}/suspend
     */
    public function suspendUser(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        $user->status = 'suspended';
        $user->note = $request->input('note', $user->note);
        $user->save();

        return response()->json(['status' => 'ok', 'user' => $user->fresh()]);
    }

    /**
     * GET /api/internal/bot/user/{tg_id}/quota
     */
    public function getUserQuota(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['ssh_limit' => 0, 'xray_limit' => 0]);
        }

        // Count active accounts
        $sshTotal = TelegramAccountRegistry::where('tg_id', $tgId)
            ->where('service', 'ssh')->where('active', true)->count();
        $xrayTotal = TelegramAccountRegistry::where('tg_id', $tgId)
            ->whereIn('service', ['vmess', 'vless', 'trojan', 'shadowsocks'])
            ->where('active', true)->count();

        return response()->json([
            'ssh_limit' => $user->ssh_limit,
            'xray_limit' => $user->xray_limit,
            'ssh_total' => $sshTotal,
            'xray_total' => $xrayTotal,
        ]);
    }

    /**
     * POST /api/internal/bot/user/{tg_id}/quota/update
     */
    public function updateUserQuota(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $user = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$user) {
            return response()->json(['error' => 'User not found'], 404);
        }

        if ($request->has('ssh_limit')) {
            $user->ssh_limit = (int)$request->input('ssh_limit');
        }
        if ($request->has('xray_limit')) {
            $user->xray_limit = (int)$request->input('xray_limit');
        }
        $user->save();

        return response()->json(['status' => 'ok', 'user' => $user->fresh()]);
    }

    // ─────────────────────────────────────────────
    // Access Requests
    // ─────────────────────────────────────────────

    /**
     * POST /api/internal/bot/access-request
     */
    public function createAccessRequest(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'reason' => 'nullable|string',
        ]);

        $ar = TelegramAccessRequest::create([
            'tg_id' => $request->input('tg_id'),
            'tg_username' => $request->input('tg_username') ?: '',
            'tg_full_name' => $request->input('tg_full_name') ?: '',
            'reason' => $request->input('reason') ?: '',
            'status' => 'pending',
        ]);

        return response()->json(['status' => 'ok', 'request' => $ar]);
    }

    /**
     * GET /api/internal/bot/access-requests
     */
    public function listAccessRequests(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $status = $request->query('status', 'pending');
        $requests = TelegramAccessRequest::where('status', $status)
            ->orderBy('created_at', 'desc')
            ->limit(50)
            ->get();

        return response()->json(['requests' => $requests]);
    }

    /**
     * POST /api/internal/bot/access-request/{id}/approve
     */
    public function approveAccessRequest(Request $request, int $id): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $req = TelegramAccessRequest::find($id);
        if (!$req) {
            return response()->json(['error' => 'Request not found'], 404);
        }

        $botUser = TelegramBotUser::firstOrCreate(
            ['tg_id' => $req->tg_id],
            [
                'tg_username' => $req->tg_username ?? '',
                'tg_full_name' => $req->tg_full_name ?? '',
                'role' => 'user',
                'status' => 'approved',
            ]
        );

        $botUser->status = 'approved';
        $botUser->save();

        // Auto-create and sync web user account
        $botUser->syncWebUser();

        $req->delete();

        return response()->json(['status' => 'ok', 'user' => $botUser->fresh(), 'request' => $req->fresh()]);
    }

    /**
     * POST /api/internal/bot/access-request/{id}/reject
     */
    public function rejectAccessRequest(Request $request, int $id): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $req = TelegramAccessRequest::find($id);
        if (!$req) {
            return response()->json(['error' => 'Request not found'], 404);
        }

        $botUser = TelegramBotUser::firstOrCreate(
            ['tg_id' => $req->tg_id],
            [
                'tg_username' => $req->tg_username ?? '',
                'tg_full_name' => $req->tg_full_name ?? '',
                'role' => 'user',
                'status' => 'rejected',
            ]
        );

        $botUser->status = 'rejected';
        $botUser->save();

        $req->delete();

        return response()->json(['status' => 'ok', 'user' => $botUser->fresh(), 'request' => $req->fresh()]);
    }

    // ─────────────────────────────────────────────
    // Quota Requests
    // ─────────────────────────────────────────────

    /**
     * POST /api/internal/bot/quota-request
     */
    public function createQuotaRequest(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $qr = TelegramQuotaRequest::create([
            'tg_id' => $request->input('tg_id'),
            'reason' => $request->input('reason', ''),
            'status' => 'pending',
        ]);

        return response()->json(['status' => 'ok', 'request' => $qr]);
    }

    /**
     * GET /api/internal/bot/quota-requests
     */
    public function listQuotaRequests(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $status = $request->query('status', 'pending');
        $requests = TelegramQuotaRequest::where('status', $status)
            ->orderBy('created_at', 'desc')
            ->limit(50)
            ->get();

        return response()->json(['requests' => $requests]);
    }

    /**
     * POST /api/internal/bot/quota-request/{id}/approve
     */
    public function approveQuotaRequest(Request $request, int $id): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $qr = TelegramQuotaRequest::find($id);
        if (!$qr) {
            return response()->json(['error' => 'Request not found'], 404);
        }

        $qr->status = 'approved';
        $qr->admin_id = $request->input('admin_id') ?: '';
        $qr->admin_reason = $request->input('note') ?: '';
        $qr->processed_at = now();
        $qr->save();

        // Update user quota
        $sshAdd = (int)$request->input('ssh_add', 0);
        $xrayAdd = (int)$request->input('xray_add', 0);
        if ($sshAdd > 0 || $xrayAdd > 0) {
            $user = TelegramBotUser::where('tg_id', $qr->tg_id)->first();
            if ($user) {
                $user->ssh_limit += $sshAdd;
                $user->xray_limit += $xrayAdd;
                $user->save();
            }
        }

        return response()->json(['status' => 'ok', 'request' => $qr->fresh()]);
    }

    /**
     * POST /api/internal/bot/quota-request/{id}/reject
     */
    public function rejectQuotaRequest(Request $request, int $id): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $qr = TelegramQuotaRequest::find($id);
        if (!$qr) {
            return response()->json(['error' => 'Request not found'], 404);
        }

        $qr->status = 'rejected';
        $qr->admin_id = $request->input('admin_id') ?: '';
        $qr->admin_reason = $request->input('note') ?: '';
        $qr->processed_at = now();
        $qr->save();

        return response()->json(['status' => 'ok', 'request' => $qr->fresh()]);
    }

    // ─────────────────────────────────────────────
    // Account Registry
    // ─────────────────────────────────────────────

    /**
     * POST /api/internal/bot/account/register
     */
    public function registerAccount(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'service' => 'required|string',
            'category' => 'nullable|string',
            'username' => 'required|string',
        ]);

        $botUser = TelegramBotUser::where('tg_id', $request->input('tg_id'))->first();
        $userId = $botUser ? $botUser->user_id : null;

        if (!$userId) {
            $admin = User::where('role', 'admin')->first();
            $userId = $admin ? $admin->id : null;
        }

        // Create VpnAccount first
        $vpnAcc = \App\Models\VpnAccount::where('vpn_username', $request->input('username'))
            ->where('service', $request->input('service'))
            ->first();

        if (!$vpnAcc) {
            $vpnAcc = \App\Models\VpnAccount::create([
                'user_id' => $userId,
                'vpn_username' => $request->input('username'),
                'service' => $request->input('service'),
            ]);
        }

        // Create TelegramAccountRegistry record
        $record = TelegramAccountRegistry::create([
            'tg_id' => $request->input('tg_id'),
            'service' => $request->input('service'),
            'category' => $request->input('category') ?: $request->input('service'),
            'username' => $request->input('username'),
            'expires_at' => $request->input('expires_at') ?: ($request->input('expiry_date') ?: ''),
            'is_trial' => $request->boolean('is_trial', false),
            'active' => true,
        ]);

        return response()->json(['status' => 'ok', 'account' => $record, 'vpn_account' => $vpnAcc]);
    }

    /**
     * POST /api/internal/bot/account/deactivate
     */
    public function deactivateAccount(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $tgId = $request->input('tg_id');
        $username = $request->input('username');
        $service = $request->input('service');

        $count = TelegramAccountRegistry::where('tg_id', $tgId)
            ->where('username', $username)
            ->where('service', $service)
            ->update(['active' => false]);

        return response()->json(['status' => 'ok', 'deactivated' => $count]);
    }

    /**
     * GET /api/internal/bot/accounts/{tg_id}
     */
    public function listAccounts(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $accounts = TelegramAccountRegistry::where('tg_id', $tgId)
            ->where('active', true)
            ->orderBy('created_at', 'desc')
            ->get();

        return response()->json(['accounts' => $accounts]);
    }

    /**
     * GET /api/internal/bot/user/{tg_id}/stats
     */
    public function getUserStats(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $sshTotal = TelegramAccountRegistry::where('tg_id', $tgId)
            ->where('service', 'ssh')->where('active', true)->count();
        $xrayTotal = TelegramAccountRegistry::where('tg_id', $tgId)
            ->whereIn('service', ['vmess', 'vless', 'trojan', 'shadowsocks'])
            ->where('active', true)->count();

        return response()->json([
            'ssh_total' => $sshTotal,
            'xray_total' => $xrayTotal,
        ]);
    }

    // ─────────────────────────────────────────────
    // Pricing
    // ─────────────────────────────────────────────

    /**
     * GET /api/internal/pricing
     */
    public function getPricing(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $prices = Price::all();

        return response()->json(['prices' => $prices]);
    }

    // ─────────────────────────────────────────────
    // Wallet
    // ─────────────────────────────────────────────

    /**
     * GET /api/internal/wallet/balance/{tg_id}
     * Get balance for a Telegram user by looking up their linked web panel user.
     */
    public function getBalance(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['balance' => 0, 'linked' => false]);
        }

        $webUser = User::find($botUser->user_id);
        if (!$webUser) {
            return response()->json(['balance' => 0, 'linked' => false]);
        }

        return response()->json([
            'balance' => (int)$webUser->balance,
            'linked' => true,
            'web_username' => $webUser->username,
        ]);
    }

    /**
     * POST /api/internal/wallet/debit
     * Deduct balance from a Telegram user's linked web panel account.
     */
    public function debitBalance(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'amount' => 'required|integer|min:1',
            'description' => 'nullable|string',
        ]);

        $tgId = $request->input('tg_id');
        $amount = (int)$request->input('amount');

        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['error' => 'Akun Telegram belum terhubung ke akun web panel. Silakan login via web terlebih dahulu.'], 400);
        }

        $webUser = User::find($botUser->user_id);
        if (!$webUser) {
            return response()->json(['error' => 'Akun web panel tidak ditemukan.'], 404);
        }

        if ($webUser->balance < $amount) {
            return response()->json(['error' => 'Saldo tidak cukup. Saldo: Rp ' . number_format($webUser->balance, 0, ',', '.') . ', Harga: Rp ' . number_format($amount, 0, ',', '.')], 400);
        }

        $webUser->balance -= $amount;
        $webUser->save();

        // Record transaction
        Transaction::create([
            'user_id' => $webUser->id,
            'type' => 'purchase',
            'total_amount' => $amount,
            'description' => $request->input('description', 'Pembelian via Bot Telegram'),
            'status' => 'success',
            'metadata' => ['source' => 'telegram_bot', 'tg_id' => $tgId],
        ]);

        return response()->json([
            'status' => 'ok',
            'new_balance' => (int)$webUser->balance,
        ]);
    }

    /**
     * POST /api/internal/wallet/topup
     * Initiate a pending topup transaction from Telegram bot.
     */
    public function topup(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'amount' => 'required|integer|min:5000',
        ]);

        $tgId = $request->input('tg_id');
        $amount = (int)$request->input('amount');

        if ($amount % 5000 !== 0) {
            return response()->json(['error' => 'Nominal top up harus kelipatan Rp 5.000'], 400);
        }

        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['error' => 'Akun Telegram Anda belum terhubung ke web panel. Silakan lakukan integrasi di Profil Pengguna.'], 400);
        }

        $webUser = User::find($botUser->user_id);
        if (!$webUser) {
            return response()->json(['error' => 'Akun web panel tidak ditemukan.'], 404);
        }

        // Cancel existing pending topups of this user
        Transaction::where('user_id', $webUser->id)
            ->where('status', 'pending')
            ->where('type', 'topup')
            ->update(['status' => 'cancelled']);

        $uniqueCode = rand(1, 100);
        $totalAmount = $amount + $uniqueCode;

        $qrisPayload = Setting::where('key', 'qris_payload')->value('value');
        if (!$qrisPayload) {
            return response()->json(['error' => 'Metode pembayaran QRIS belum dikonfigurasi oleh admin.'], 400);
        }

        // Generate dynamic QRIS string
        $dynamicQris = \App\Helpers\QrisHelper::generateDynamic($qrisPayload, $totalAmount);

        // Create transaction
        $transaction = Transaction::create([
            'reference' => 'TOP-BOT-' . strtoupper(\Illuminate\Support\Str::random(10)),
            'user_id' => $webUser->id,
            'type' => 'topup',
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'status' => 'pending',
            'description' => 'Top Up Saldo via Bot Telegram',
            'metadata' => ['source' => 'telegram_bot', 'tg_id' => $tgId],
        ]);

        return response()->json([
            'status' => 'ok',
            'reference' => $transaction->reference,
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'dynamic_qris' => $dynamicQris,
            'qr_code_url' => 'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=' . urlencode($dynamicQris),
        ]);
    }

    /**
     * POST /api/internal/wallet/vpn_qris
     * Create a pending QRIS transaction for direct VPN order.
     */
    public function vpnPurchaseQris(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'amount' => 'required|integer',
            'protocol' => 'required|string',
            'days' => 'required|integer',
            'ip_limit' => 'required|integer',
        ]);

        $tgId = $request->input('tg_id');
        $amount = (int)$request->input('amount');
        
        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['error' => 'Akun Telegram belum terhubung ke web panel.'], 400);
        }
        
        $webUser = User::find($botUser->user_id);
        if (!$webUser) {
            return response()->json(['error' => 'Akun web panel tidak ditemukan.'], 404);
        }
        
        $qrisPayload = Setting::where('key', 'qris_payload')->value('value');
        if (!$qrisPayload) {
            return response()->json(['error' => 'Metode pembayaran QRIS belum dikonfigurasi admin.'], 400);
        }
        
        // Cancel previous pending vpn_purchase_qris for this user
        Transaction::where('user_id', $webUser->id)
            ->where('status', 'pending')
            ->where('type', 'vpn_purchase_qris')
            ->update(['status' => 'cancelled']);
            
        $uniqueCode = rand(1, 100);
        $totalAmount = $amount + $uniqueCode;
        
        $dynamicQris = \App\Helpers\QrisHelper::generateDynamic($qrisPayload, $totalAmount);
        
        $transaction = Transaction::create([
            'reference' => 'VPN-QRIS-' . strtoupper(\Illuminate\Support\Str::random(8)),
            'user_id' => $webUser->id,
            'type' => 'vpn_purchase_qris',
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'status' => 'pending',
            'description' => 'Beli VPN via QRIS - ' . strtoupper($request->protocol),
            'metadata' => [
                'source' => 'telegram_bot',
                'tg_id' => $tgId,
                'protocol' => $request->protocol,
                'days' => $request->days,
                'ip_limit' => $request->ip_limit,
            ],
        ]);
        
        return response()->json([
            'status' => 'ok',
            'reference' => $transaction->reference,
            'amount' => $amount,
            'unique_code' => $uniqueCode,
            'total_amount' => $totalAmount,
            'dynamic_qris' => $dynamicQris,
            'qr_code_url' => 'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=' . urlencode($dynamicQris),
        ]);
    }

    /**
     * POST /api/internal/wallet/voucher/redeem
     * Redeem a voucher code for a Telegram user.
     */
    public function redeemVoucher(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'tg_id' => 'required|string',
            'voucher_code' => 'required|string|max:30',
        ]);

        $tgId = $request->input('tg_id');
        $code = strtoupper(trim($request->input('voucher_code')));

        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['error' => 'Akun Telegram Anda belum terhubung ke web panel.'], 400);
        }

        $webUser = User::find($botUser->user_id);
        if (!$webUser) {
            return response()->json(['error' => 'Akun web panel tidak ditemukan.'], 404);
        }

        $voucher = \App\Models\Voucher::where('code', $code)->first();

        if (!$voucher) {
            return response()->json(['error' => 'Kode voucher tidak ditemukan!'], 404);
        }

        if (!$voucher->is_active) {
            return response()->json(['error' => 'Voucher ini sudah tidak aktif!'], 400);
        }

        if ($voucher->used_count >= $voucher->usage_limit) {
            return response()->json(['error' => 'Kuota penggunaan voucher ini sudah habis!'], 400);
        }

        if ($voucher->expires_at && $voucher->expires_at->isPast()) {
            return response()->json(['error' => 'Voucher ini sudah kedaluwarsa!'], 400);
        }

        $alreadyUsed = \App\Models\VoucherUsage::where('user_id', $webUser->id)
            ->where('voucher_id', $voucher->id)
            ->exists();
        if ($alreadyUsed) {
            return response()->json(['error' => 'Anda sudah pernah menggunakan voucher ini!'], 400);
        }

        if ($voucher->type === 'free_balance') {
            // Add balance
            $webUser->balance += $voucher->benefit_value;
            $webUser->save();

            // Log voucher usage
            \App\Models\VoucherUsage::create([
                'user_id' => $webUser->id,
                'voucher_id' => $voucher->id,
                'benefit_type' => 'free_balance',
                'benefit_amount' => $voucher->benefit_value,
            ]);

            $voucher->increment('used_count');

            // Create successful transaction log
            Transaction::create([
                'reference' => 'VCH-' . strtoupper(\Illuminate\Support\Str::random(10)),
                'user_id' => $webUser->id,
                'type' => 'topup',
                'amount' => $voucher->benefit_value,
                'unique_code' => 0,
                'total_amount' => $voucher->benefit_value,
                'status' => 'success',
                'description' => "Klaim Voucher Saldo Gratis ({$voucher->code}) via Bot",
            ]);

            return response()->json([
                'status' => 'ok',
                'message' => 'Voucher berhasil diklaim! Saldo gratis Rp ' . number_format($voucher->benefit_value, 0, ',', '.') . ' telah ditambahkan ke dompet Anda.',
                'new_balance' => (int)$webUser->balance,
            ]);
        } elseif ($voucher->type === 'double_saldo') {
            return response()->json(['error' => 'Voucher Double Saldo hanya dapat digunakan pada menu Top Up.'], 400);
        }

        return response()->json(['error' => 'Tipe voucher tidak didukung di bot.'], 400);
    }

    // ─────────────────────────────────────────────
    // Transactions
    // ─────────────────────────────────────────────

    /**
     * GET /api/internal/transaction/history/{tg_id}
     */
    public function transactionHistory(Request $request, string $tgId): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $botUser = TelegramBotUser::where('tg_id', $tgId)->first();
        if (!$botUser || !$botUser->user_id) {
            return response()->json(['transactions' => []]);
        }

        $transactions = Transaction::where('user_id', $botUser->user_id)
            ->orderBy('created_at', 'desc')
            ->limit(10)
            ->get();

        return response()->json(['transactions' => $transactions]);
    }
    /**
     * GET /api/internal/transaction/status/{reference}
     */
    public function transactionStatus(Request $request, string $reference): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $transaction = Transaction::where('reference', $reference)->first();
        if (!$transaction) {
            return response()->json(['error' => 'Transaksi tidak ditemukan'], 404);
        }

        return response()->json([
            'reference' => $transaction->reference,
            'status' => $transaction->status,
            'type' => $transaction->type,
            'amount' => $transaction->total_amount,
        ]);
    }

    /**
     * POST /api/internal/transaction/cancel
     */
    public function transactionCancel(Request $request): JsonResponse
    {
        if (!$this->authorize($request)) return $this->unauthorized();

        $request->validate([
            'reference' => 'required|string',
        ]);

        $reference = $request->input('reference');
        $transaction = Transaction::where('reference', $reference)->where('status', 'pending')->first();
        
        if (!$transaction) {
            return response()->json(['error' => 'Transaksi tidak ditemukan atau sudah tidak pending'], 404);
        }

        $transaction->status = 'cancelled';
        $transaction->save();

        return response()->json(['status' => 'ok', 'message' => 'Transaksi berhasil dibatalkan']);
    }
}
