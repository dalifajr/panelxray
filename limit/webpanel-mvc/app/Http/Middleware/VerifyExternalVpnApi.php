<?php

namespace App\Http\Middleware;

use App\Models\Setting;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Crypt;
use Symfony\Component\HttpFoundation\Response;

class VerifyExternalVpnApi
{
    public const MAX_CLOCK_SKEW_SECONDS = 60;
    public const NONCE_TTL_SECONDS = 180;

    public function handle(Request $request, Closure $next): Response
    {
        $enabled = Setting::where('key', 'external_api_enabled')->value('value');
        if ($enabled !== 'true') {
            return response()->json([
                'success' => false,
                'message' => 'External VPN API is disabled on this panel.',
                'data' => null,
            ], 503);
        }

        // Optional IP Allowlist check
        $allowlistRaw = (string) (Setting::where('key', 'external_api_ip_allowlist')->value('value') ?? '');
        $allowedIps = array_values(array_filter(array_map('trim', preg_split('/[\r\n,]+/', $allowlistRaw))));
        if (!empty($allowedIps)) {
            $clientIp = (string) $request->ip();
            if (!$this->ipMatchesAllowlist($clientIp, $allowedIps)) {
                return response()->json([
                    'success' => false,
                    'message' => 'IP address is not allowed.',
                    'data' => null,
                ], 403);
            }
        }

        // 1. Verify Bearer Token against SHA-256 hash
        $tokenHash = (string) (Setting::where('key', 'external_api_token_hash')->value('value') ?? '');
        $bearer = (string) ($request->bearerToken() ?? '');

        if ($tokenHash === '' || $bearer === '' || !hash_equals($tokenHash, hash('sha256', $bearer))) {
            return response()->json([
                'success' => false,
                'message' => 'Unauthorized: invalid API token.',
                'data' => null,
            ], 401);
        }

        // 2. Verify HMAC-SHA256 Signature + Anti-Replay Timestamp & Nonce
        $hmacSecret = $this->resolveHmacSecret();
        if ($hmacSecret === '') {
            return response()->json([
                'success' => false,
                'message' => 'External API HMAC secret is not configured.',
                'data' => null,
            ], 503);
        }

        $timestamp = (string) $request->header('X-VPN-Timestamp', '');
        $nonce = (string) $request->header('X-VPN-Nonce', '');
        $signature = strtolower((string) $request->header('X-VPN-Signature', ''));

        if ($timestamp === '' || !ctype_digit($timestamp)) {
            return response()->json([
                'success' => false,
                'message' => 'Missing or invalid X-VPN-Timestamp header.',
                'data' => null,
            ], 401);
        }

        $tsInt = (int) $timestamp;
        if (abs(time() - $tsInt) > self::MAX_CLOCK_SKEW_SECONDS) {
            return response()->json([
                'success' => false,
                'message' => 'Request timestamp expired or outside allowed skew window.',
                'data' => null,
            ], 401);
        }

        if ($nonce === '' || !preg_match('/^[a-zA-Z0-9._-]{12,128}$/', $nonce)) {
            return response()->json([
                'success' => false,
                'message' => 'Missing or invalid X-VPN-Nonce header.',
                'data' => null,
            ], 401);
        }

        if ($signature === '' || !preg_match('/^[a-f0-9]{64}$/', $signature)) {
            return response()->json([
                'success' => false,
                'message' => 'Missing or invalid X-VPN-Signature header.',
                'data' => null,
            ], 401);
        }

        $method = strtoupper($request->getMethod());
        $requestUri = '/' . ltrim($request->getRequestUri(), '/');
        $bodyHash = hash('sha256', (string) $request->getContent());
        $canonical = implode("\n", [$method, $requestUri, $timestamp, $nonce, $bodyHash]);
        $expectedSignature = hash_hmac('sha256', $canonical, $hmacSecret);

        if (!hash_equals($expectedSignature, $signature)) {
            return response()->json([
                'success' => false,
                'message' => 'Unauthorized: invalid HMAC signature.',
                'data' => null,
            ], 401);
        }

        // Prevent replay attacks by locking the nonce for NONCE_TTL_SECONDS
        $nonceCacheKey = 'ext_vpn_api_nonce:' . hash('sha256', $nonce);
        if (!Cache::add($nonceCacheKey, 1, self::NONCE_TTL_SECONDS)) {
            return response()->json([
                'success' => false,
                'message' => 'Replay detected: request nonce already used.',
                'data' => null,
            ], 401);
        }

        return $next($request);
    }

    private function resolveHmacSecret(): string
    {
        $raw = (string) (Setting::where('key', 'external_api_hmac_secret')->value('value') ?? '');
        if ($raw === '') {
            return '';
        }

        try {
            return Crypt::decryptString($raw);
        } catch (\Throwable $e) {
            // Allow unencrypted fallback only if migrated/seeded directly
            return $raw;
        }
    }

    private function ipMatchesAllowlist(string $clientIp, array $allowedIps): bool
    {
        foreach ($allowedIps as $rule) {
            if ($rule === $clientIp) {
                return true;
            }
            if (str_contains($rule, '/') && $this->ipInCidr($clientIp, $rule)) {
                return true;
            }
        }

        return false;
    }

    private function ipInCidr(string $ip, string $cidr): bool
    {
        [$subnet, $bits] = array_pad(explode('/', $cidr, 2), 2, null);
        if ($bits === null || !ctype_digit($bits)) {
            return false;
        }

        $ipLong = ip2long($ip);
        $subnetLong = ip2long($subnet);
        if ($ipLong === false || $subnetLong === false) {
            return false;
        }

        $bitsInt = (int) $bits;
        if ($bitsInt < 0 || $bitsInt > 32) {
            return false;
        }

        $mask = $bitsInt === 0 ? 0 : (~0 << (32 - $bitsInt));
        return ($ipLong & $mask) === ($subnetLong & $mask);
    }
}
