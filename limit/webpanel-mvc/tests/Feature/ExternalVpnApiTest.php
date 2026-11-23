<?php

namespace Tests\Feature;

use App\Models\Setting;
use App\Services\VpnService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Str;
use Mockery;
use Tests\TestCase;

class ExternalVpnApiTest extends TestCase
{
    use RefreshDatabase;

    private string $token = 'vpnx_test_bearer_token_1234567890abcdef';
    private string $hmacSecret = 'test_hmac_secret_key_0123456789abcdef0123456789abcdef';

    protected function setUp(): void
    {
        parent::setUp();

        Setting::updateOrCreate(['key' => 'external_api_enabled'], ['value' => 'true']);
        Setting::updateOrCreate(['key' => 'external_api_token_hash'], ['value' => hash('sha256', $this->token)]);
        Setting::updateOrCreate(['key' => 'external_api_hmac_secret'], ['value' => Crypt::encryptString($this->hmacSecret)]);
        Setting::updateOrCreate(['key' => 'external_api_ip_allowlist'], ['value' => '']);
    }

    private function signedHeaders(string $method, string $uri, string $rawBody = '', ?int $timestamp = null, ?string $nonce = null, ?string $token = null, ?string $secret = null): array
    {
        $ts = (string) ($timestamp ?? time());
        $n = $nonce ?? ('nonce_' . Str::random(24));
        $bodyHash = hash('sha256', $rawBody);
        $canonical = implode("\n", [strtoupper($method), '/' . ltrim($uri, '/'), $ts, $n, $bodyHash]);
        $sig = hash_hmac('sha256', $canonical, $secret ?? $this->hmacSecret);

        return [
            'Authorization' => 'Bearer ' . ($token ?? $this->token),
            'X-VPN-Timestamp' => $ts,
            'X-VPN-Nonce' => $n,
            'X-VPN-Signature' => $sig,
            'Accept' => 'application/json',
        ];
    }

    public function test_rejects_requests_when_api_disabled(): void
    {
        Setting::where('key', 'external_api_enabled')->update(['value' => 'false']);

        $headers = $this->signedHeaders('GET', '/api/v1/vpn/health');
        $this->withHeaders($headers)
            ->get('/api/v1/vpn/health')
            ->assertStatus(503)
            ->assertJsonPath('success', false);
    }

    public function test_rejects_invalid_bearer_token_hmac_timestamp_and_nonce_replay(): void
    {
        $mock = Mockery::mock(VpnService::class);
        $mock->shouldReceive('executeBash')->andReturn(['success' => true, 'output' => "BRIDGE_OK\nDOMAIN=sg1.example.com\nXRAY=active\nSSH=active", 'error' => '']);
        $mock->shouldReceive('getAccounts')->andReturn([]);
        $this->app->instance(VpnService::class, $mock);

        // Wrong token
        $this->withHeaders($this->signedHeaders('GET', '/api/v1/vpn/health', '', null, null, 'wrong_token'))
            ->get('/api/v1/vpn/health')
            ->assertStatus(401);

        // Wrong HMAC
        $this->withHeaders($this->signedHeaders('GET', '/api/v1/vpn/health', '', null, null, null, 'wrong_secret'))
            ->get('/api/v1/vpn/health')
            ->assertStatus(401);

        // Expired timestamp (> 60s)
        $this->withHeaders($this->signedHeaders('GET', '/api/v1/vpn/health', '', time() - 120))
            ->get('/api/v1/vpn/health')
            ->assertStatus(401);

        // Valid request succeeds, then same nonce replay is rejected
        $fixedNonce = 'nonce_replay_check_123456789';
        $headers = $this->signedHeaders('GET', '/api/v1/vpn/health', '', time(), $fixedNonce);

        $this->withHeaders($headers)
            ->get('/api/v1/vpn/health')
            ->assertStatus(200)
            ->assertJsonPath('success', true)
            ->assertJsonPath('data.bridge_ok', true);

        $this->withHeaders($headers)
            ->get('/api/v1/vpn/health')
            ->assertStatus(401)
            ->assertJsonPath('success', false);
    }

    public function test_ip_allowlist_blocks_unauthorized_ip(): void
    {
        Setting::where('key', 'external_api_ip_allowlist')->update(['value' => '10.99.0.1']);

        $headers = $this->signedHeaders('GET', '/api/v1/vpn/health');
        $this->withHeaders($headers)
            ->get('/api/v1/vpn/health')
            ->assertStatus(403)
            ->assertJsonPath('success', false);
    }

    public function test_rejects_shell_injection_username(): void
    {
        $payload = json_encode([
            'protocol' => 'vmess',
            'username' => 'bad;rm -rf /',
            'days' => 30,
        ]);

        $headers = array_merge(
            $this->signedHeaders('POST', '/api/v1/vpn/accounts', $payload),
            ['Content-Type' => 'application/json']
        );

        $this->call('POST', '/api/v1/vpn/accounts', [], [], [], $this->transformHeadersToServerVars($headers), $payload)
            ->assertStatus(422);
    }

    public function test_full_vpn_lifecycle_and_idempotency_replay(): void
    {
        $mock = Mockery::mock(VpnService::class);
        $mock->shouldReceive('runPython')->andReturnUsing(function (string $script) {
            if (str_contains($script, '"in_db"')) {
                return ['success' => true, 'output' => json_encode(['in_db' => false, 'in_xray' => false]), 'error' => ''];
            }
            if (str_contains($script, "'domain': domain")) {
                return ['success' => true, 'output' => json_encode([
                    'success' => true,
                    'domain' => 'sg1.vpn.test',
                    'uuid' => '11111111-2222-3333-4444-555555555555',
                    'quota' => 50,
                    'ip_limit' => 2,
                    'expires_at' => '2026-12-23',
                    'suspended' => false,
                    'username' => 'alice_01',
                    'service' => 'vmess',
                ]), 'error' => ''];
            }
            return ['success' => true, 'output' => 'OK', 'error' => ''];
        });

        $mock->shouldReceive('executeBashWithStdin')
            ->once() // proves Idempotency-Key prevented double execution!
            ->with('addws', Mockery::type('string'))
            ->andReturn(['success' => true, 'output' => 'CREATED', 'error' => '']);

        $mock->shouldReceive('getAccounts')->andReturn([
            [
                'service' => 'vmess',
                'username' => 'alice_01',
                'active' => 1,
                'created_at' => '2026-11-23',
                'expires_at' => '2026-12-23',
                'ip_limit' => 2,
                'quota' => 50,
            ],
        ]);

        $mock->shouldReceive('renewXrayAccount')
            ->once()
            ->with('vmess', 'alice_01', 30, 50, 2)
            ->andReturn(['success' => true, 'expires_at' => '2027-01-22']);

        $mock->shouldReceive('executeBash')->andReturn(['success' => true, 'output' => 'OK', 'error' => '']);

        $this->app->instance(VpnService::class, $mock);

        // 1. Create with Idempotency-Key
        $createPayload = json_encode([
            'protocol' => 'vmess',
            'username' => 'alice_01',
            'days' => 30,
            'quota_gb' => 50,
            'ip_limit' => 2,
            'sni_mode' => '3',
            'external_ref' => 'ORD-1001',
        ]);

        $createHeaders1 = array_merge(
            $this->signedHeaders('POST', '/api/v1/vpn/accounts', $createPayload),
            ['Content-Type' => 'application/json', 'Idempotency-Key' => 'order-1001-create']
        );

        $res1 = $this->call('POST', '/api/v1/vpn/accounts', [], [], [], $this->transformHeadersToServerVars($createHeaders1), $createPayload);
        $res1->assertStatus(201)
            ->assertJsonPath('success', true)
            ->assertJsonPath('data.username', 'alice_01')
            ->assertJsonPath('data.uuid', '11111111-2222-3333-4444-555555555555')
            ->assertJsonPath('data.domain', 'sg1.vpn.test')
            ->assertJsonPath('data.sni_mode', '3');
        $this->assertStringStartsWith('vmess://', (string) $res1->json('data.links.tls'));

        // Replay same Idempotency-Key with new nonce -> returns cached 201 without calling addws again
        $createHeaders2 = array_merge(
            $this->signedHeaders('POST', '/api/v1/vpn/accounts', $createPayload),
            ['Content-Type' => 'application/json', 'Idempotency-Key' => 'order-1001-create']
        );
        $this->call('POST', '/api/v1/vpn/accounts', [], [], [], $this->transformHeadersToServerVars($createHeaders2), $createPayload)
            ->assertStatus(201)
            ->assertHeader('X-Idempotent-Replay', 'true');

        // 2. List accounts
        $listHeaders = $this->signedHeaders('GET', '/api/v1/vpn/accounts?protocol=vmess');
        $this->withHeaders($listHeaders)
            ->get('/api/v1/vpn/accounts?protocol=vmess')
            ->assertStatus(200)
            ->assertJsonPath('data.count', 1);

        // 3. Renew
        $renewPayload = json_encode(['days' => 30, 'quota_gb' => 50, 'ip_limit' => 2]);
        $renewHeaders = array_merge(
            $this->signedHeaders('POST', '/api/v1/vpn/accounts/vmess/alice_01/renew', $renewPayload),
            ['Content-Type' => 'application/json', 'Idempotency-Key' => 'renew-1001']
        );
        $this->call('POST', '/api/v1/vpn/accounts/vmess/alice_01/renew', [], [], [], $this->transformHeadersToServerVars($renewHeaders), $renewPayload)
            ->assertStatus(200)
            ->assertJsonPath('data.expired_at', '2027-01-22');

        // 4. Suspend
        $suspPayload = json_encode(['reason' => 'admin_policy', 'admin_suspended' => true]);
        $suspHeaders = array_merge(
            $this->signedHeaders('POST', '/api/v1/vpn/accounts/vmess/alice_01/suspend', $suspPayload),
            ['Content-Type' => 'application/json']
        );
        $this->call('POST', '/api/v1/vpn/accounts/vmess/alice_01/suspend', [], [], [], $this->transformHeadersToServerVars($suspHeaders), $suspPayload)
            ->assertStatus(200)
            ->assertJsonPath('data.status', 'suspended');

        // 5. Unsuspend
        $unsuspHeaders = $this->signedHeaders('POST', '/api/v1/vpn/accounts/vmess/alice_01/unsuspend');
        $this->withHeaders($unsuspHeaders)
            ->post('/api/v1/vpn/accounts/vmess/alice_01/unsuspend')
            ->assertStatus(200)
            ->assertJsonPath('data.status', 'active');

        // 6. Delete
        $delHeaders = $this->signedHeaders('DELETE', '/api/v1/vpn/accounts/vmess/alice_01');
        $this->withHeaders($delHeaders)
            ->delete('/api/v1/vpn/accounts/vmess/alice_01')
            ->assertStatus(200)
            ->assertJsonPath('data.deleted', true);
    }

    public function test_list_accounts_with_include_config_returns_bulk_config_details(): void
    {
        $mock = Mockery::mock(VpnService::class);
        $mock->shouldReceive('getAccounts')->with('vmess')->andReturn([
            [
                'service' => 'vmess',
                'username' => 'bulk_vmess_01',
                'active' => 1,
                'created_at' => '2026-11-23',
                'expires_at' => '2026-12-23',
                'ip_limit' => 2,
                'quota' => 100,
            ],
        ]);
        $mock->shouldReceive('runPython')->once()->andReturn([
            'success' => true,
            'output' => json_encode([
                'domain' => 'sg1.vpn.test',
                'uuids' => [
                    'vmess:bulk_vmess_01' => '11111111-2222-3333-4444-555555555555',
                ],
            ]),
            'error' => '',
        ]);

        $this->app->instance(VpnService::class, $mock);

        $uri = '/api/v1/vpn/accounts?protocol=vmess&include_config=1';
        $headers = $this->signedHeaders('GET', $uri);

        $res = $this->withHeaders($headers)->get($uri);
        $res->assertStatus(200)
            ->assertJsonPath('success', true)
            ->assertJsonPath('data.count', 1)
            ->assertJsonPath('data.accounts.0.username', 'bulk_vmess_01')
            ->assertJsonPath('data.accounts.0.domain', 'sg1.vpn.test')
            ->assertJsonPath('data.accounts.0.uuid', '11111111-2222-3333-4444-555555555555');

        $this->assertStringStartsWith('vmess://', (string) $res->json('data.accounts.0.links.tls'));
        $this->assertStringContainsString('bulk_vmess_01', (string) $res->json('data.accounts.0.formatted_text'));
    }
}
