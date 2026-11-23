<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\VpnAccountManager;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use InvalidArgumentException;

class ExternalVpnApiController extends Controller
{
    public const IDEMPOTENCY_TTL_SECONDS = 86400; // 24 hours

    public function __construct(
        protected VpnAccountManager $manager
    ) {}

    public function health(): JsonResponse
    {
        $health = $this->manager->health();

        return response()->json([
            'success' => $health['bridge_ok'],
            'message' => $health['bridge_ok'] ? 'Panel and VPN bridge are healthy.' : 'VPN bridge is unreachable.',
            'data' => $health,
        ], $health['bridge_ok'] ? 200 : 503);
    }

    public function checkUsername(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'username' => ['required', 'string', 'regex:' . VpnAccountManager::USERNAME_REGEX],
            'protocol' => ['nullable', 'string', 'in:all,ssh,vmess,vless,trojan,shadowsocks'],
        ]);

        $result = $this->manager->checkUsername($validated['username'], $validated['protocol'] ?? null);

        return response()->json([
            'success' => true,
            'message' => $result['available'] ? 'Username is available.' : 'Username already exists.',
            'data' => $result,
        ]);
    }

    public function index(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'protocol' => ['nullable', 'string', 'in:all,ssh,vmess,vless,trojan,shadowsocks'],
            'status' => ['nullable', 'string', 'in:all,active,suspended,expired'],
            'search' => ['nullable', 'string', 'max:64'],
            'include_config' => ['nullable'],
        ]);

        $accounts = $this->manager->listAccounts(
            $validated['protocol'] ?? null,
            $validated['status'] ?? null,
            $validated['search'] ?? null,
            $request->boolean('include_config', false)
        );

        return response()->json([
            'success' => true,
            'message' => 'Accounts retrieved successfully.',
            'data' => [
                'count' => count($accounts),
                'accounts' => $accounts,
            ],
        ]);
    }

    public function show(Request $request, string $protocol, string $username): JsonResponse
    {
        try {
            $sniMode = (string) $request->query('sni_mode', '3');
            $detail = $this->manager->getAccountDetail($protocol, $username, $sniMode);
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        }

        if (!$detail) {
            return $this->error('VPN account not found.', 404);
        }

        return response()->json([
            'success' => true,
            'message' => 'Account detail retrieved successfully.',
            'data' => $detail,
        ]);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'protocol' => ['required', 'string', 'in:ssh,vmess,vless,trojan,shadowsocks'],
            'username' => ['required', 'string', 'regex:' . VpnAccountManager::USERNAME_REGEX],
            'password' => ['required_if:protocol,ssh', 'nullable', 'string', 'min:1', 'max:64'],
            'days' => ['required', 'integer', 'min:1', 'max:365'],
            'quota_gb' => ['nullable', 'integer', 'min:0', 'max:10000'],
            'ip_limit' => ['nullable', 'integer', 'min:1', 'max:50'],
            'sni_mode' => ['nullable', 'string', 'in:1,2,3'],
            'external_ref' => ['nullable', 'string', 'max:120'],
        ]);

        $idempotencyKey = $this->extractIdempotencyKey($request, 'create');
        if ($idempotencyKey !== null) {
            $cached = Cache::get($idempotencyKey);
            if (is_array($cached)) {
                return response()->json($cached['body'], $cached['status'])
                    ->header('X-Idempotent-Replay', 'true');
            }
        }

        try {
            $detail = $this->manager->createAccount($validated);
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        } catch (\RuntimeException $e) {
            $code = in_array($e->getCode(), [404, 409, 422, 502, 503], true) ? $e->getCode() : 500;
            return $this->error($e->getMessage(), $code);
        }

        $body = [
            'success' => true,
            'message' => 'VPN account created successfully.',
            'data' => $detail,
        ];

        if ($idempotencyKey !== null) {
            Cache::put($idempotencyKey, ['status' => 201, 'body' => $body], self::IDEMPOTENCY_TTL_SECONDS);
        }

        return response()->json($body, 201);
    }

    public function renew(Request $request, string $protocol, string $username): JsonResponse
    {
        $validated = $request->validate([
            'days' => ['required', 'integer', 'min:1', 'max:365'],
            'quota_gb' => ['nullable', 'integer', 'min:0', 'max:10000'],
            'ip_limit' => ['nullable', 'integer', 'min:1', 'max:50'],
        ]);

        $idempotencyKey = $this->extractIdempotencyKey($request, "renew:{$protocol}:{$username}");
        if ($idempotencyKey !== null) {
            $cached = Cache::get($idempotencyKey);
            if (is_array($cached)) {
                return response()->json($cached['body'], $cached['status'])
                    ->header('X-Idempotent-Replay', 'true');
            }
        }

        try {
            $result = $this->manager->renewAccount(
                $protocol,
                $username,
                (int) $validated['days'],
                isset($validated['quota_gb']) ? (int) $validated['quota_gb'] : null,
                isset($validated['ip_limit']) ? (int) $validated['ip_limit'] : null
            );
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        } catch (\RuntimeException $e) {
            $code = in_array($e->getCode(), [404, 409, 422, 502, 503], true) ? $e->getCode() : 500;
            return $this->error($e->getMessage(), $code);
        }

        $body = [
            'success' => true,
            'message' => 'VPN account renewed successfully.',
            'data' => $result,
        ];

        if ($idempotencyKey !== null) {
            Cache::put($idempotencyKey, ['status' => 200, 'body' => $body], self::IDEMPOTENCY_TTL_SECONDS);
        }

        return response()->json($body);
    }

    public function suspend(Request $request, string $protocol, string $username): JsonResponse
    {
        $validated = $request->validate([
            'reason' => ['nullable', 'string', 'max:120'],
            'admin_suspended' => ['nullable', 'boolean'],
        ]);

        try {
            $result = $this->manager->suspendAccount(
                $protocol,
                $username,
                $validated['reason'] ?? null,
                (bool) ($validated['admin_suspended'] ?? true)
            );
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        } catch (\RuntimeException $e) {
            $code = in_array($e->getCode(), [404, 409, 422, 502, 503], true) ? $e->getCode() : 500;
            return $this->error($e->getMessage(), $code);
        }

        return response()->json([
            'success' => true,
            'message' => 'VPN account suspended successfully.',
            'data' => $result,
        ]);
    }

    public function unsuspend(string $protocol, string $username): JsonResponse
    {
        try {
            $result = $this->manager->unsuspendAccount($protocol, $username);
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        } catch (\RuntimeException $e) {
            $code = in_array($e->getCode(), [404, 409, 422, 502, 503], true) ? $e->getCode() : 500;
            return $this->error($e->getMessage(), $code);
        }

        return response()->json([
            'success' => true,
            'message' => 'VPN account reactivated successfully.',
            'data' => $result,
        ]);
    }

    public function destroy(string $protocol, string $username): JsonResponse
    {
        try {
            $result = $this->manager->deleteAccount($protocol, $username);
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        } catch (\RuntimeException $e) {
            $code = in_array($e->getCode(), [404, 409, 422, 502, 503], true) ? $e->getCode() : 500;
            return $this->error($e->getMessage(), $code);
        }

        return response()->json([
            'success' => true,
            'message' => 'VPN account deleted successfully.',
            'data' => $result,
        ]);
    }

    public function traffic(): JsonResponse
    {
        $stats = $this->manager->getTrafficStats();

        return response()->json([
            'success' => true,
            'message' => 'Traffic statistics retrieved successfully.',
            'data' => $stats,
        ]);
    }

    public function devices(Request $request, string $protocol, string $username): JsonResponse
    {
        $windowMinutes = max(5, min(1440, (int) $request->query('window_minutes', 60)));

        try {
            $data = $this->manager->getAccountDevices($protocol, $username, $windowMinutes);
        } catch (InvalidArgumentException $e) {
            return $this->error($e->getMessage(), 422);
        }

        return response()->json([
            'success' => true,
            'message' => 'Device activity log retrieved successfully.',
            'data' => $data,
        ]);
    }

    private function extractIdempotencyKey(Request $request, string $scope): ?string
    {
        $raw = trim((string) $request->header('Idempotency-Key', ''));
        if ($raw === '' || strlen($raw) > 128) {
            return null;
        }
        return 'ext_vpn_idem:' . hash('sha256', $scope . ':' . $raw);
    }

    private function error(string $message, int $status): JsonResponse
    {
        return response()->json([
            'success' => false,
            'message' => $message,
            'data' => null,
        ], $status);
    }
}
