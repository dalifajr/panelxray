<?php

namespace Tests\Feature;

use App\Models\User;
use App\Models\Voucher;
use App\Models\Transaction;
use App\Models\VoucherUsage;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class VoucherTest extends TestCase
{
    use RefreshDatabase;

    public function test_customer_can_redeem_free_balance_voucher_instantly()
    {
        $user = User::create([
            'username' => 'testcustomer',
            'email' => 'test@customer.com',
            'password' => bcrypt('password123'),
            'role' => 'customer',
            'balance' => 0,
        ]);

        $voucher = Voucher::create([
            'code' => 'FREE10K',
            'type' => 'free_balance',
            'benefit_value' => 10000,
            'usage_limit' => 5,
            'used_count' => 0,
            'is_active' => true,
        ]);

        $response = $this->actingAs($user)
            ->post(route('wallet.voucher.redeem'), [
                'voucher_code' => 'FREE10K',
            ]);

        $response->assertRedirect();
        $response->assertSessionHas('sweet_success');

        // Verify balance
        $user->refresh();
        $this->assertEquals(10000, $user->balance);

        // Verify voucher usages
        $this->assertEquals(1, VoucherUsage::count());
        $this->assertEquals(1, $voucher->refresh()->used_count);

        // Verify transaction
        $this->assertEquals(2, Transaction::count()); // 1 for user claim free_balance, 1 because topup creation in WalletController topup method is also executed
    }

    public function test_double_saldo_voucher_cannot_be_redeemed_directly()
    {
        $user = User::create([
            'username' => 'testcustomer',
            'email' => 'test@customer.com',
            'password' => bcrypt('password123'),
            'role' => 'customer',
            'balance' => 0,
        ]);

        $voucher = Voucher::create([
            'code' => 'DOUBLEMAX',
            'type' => 'double_saldo',
            'benefit_value' => 50000,
            'usage_limit' => 5,
            'used_count' => 0,
            'is_active' => true,
        ]);

        $response = $this->actingAs($user)
            ->post(route('wallet.voucher.redeem'), [
                'voucher_code' => 'DOUBLEMAX',
            ]);

        $response->assertRedirect();
        $response->assertSessionHas('sweet_error');

        $user->refresh();
        $this->assertEquals(0, $user->balance);
        $this->assertEquals(0, VoucherUsage::count());
    }

    public function test_double_saldo_applied_to_topup_and_processed()
    {
        $user = User::create([
            'username' => 'testcustomer',
            'email' => 'test@customer.com',
            'password' => bcrypt('password123'),
            'role' => 'customer',
            'balance' => 0,
        ]);

        $voucher = Voucher::create([
            'code' => 'DOUBLEMAX',
            'type' => 'double_saldo',
            'benefit_value' => 50000,
            'usage_limit' => 5,
            'used_count' => 0,
            'is_active' => true,
        ]);

        // 1. Initiate Top Up with voucher code
        $response = $this->actingAs($user)
            ->post(route('wallet.topup'), [
                'amount' => 15000,
                'voucher_code' => 'DOUBLEMAX',
            ]);

        $response->assertRedirect();
        $response->assertSessionHas('sweet_success');

        // Check pending transaction created with applied voucher in metadata
        $transaction = Transaction::where('status', 'pending')->first();
        $this->assertNotNull($transaction);
        $this->assertEquals(15000, $transaction->amount);
        $this->assertEquals('double_saldo', $transaction->metadata['applied_voucher']['type']);

        // 2. Approve top-up manually (like an admin)
        $admin = User::create([
            'username' => 'admin',
            'email' => 'admin@admin.com',
            'password' => bcrypt('password123'),
            'role' => 'admin',
            'balance' => 0,
        ]);

        $responseApprove = $this->actingAs($admin)
            ->post(route('admin.orders.approve', $transaction->id));

        $responseApprove->assertRedirect();
        $responseApprove->assertSessionHas('sweet_success');

        // Verify balance (deposited amount 15000 + unique code e.g. 1..100) + double bonus 15000
        $user->refresh();
        $expectedTotalAmount = $transaction->total_amount;
        $expectedBonus = 15000;
        $this->assertEquals($expectedTotalAmount + $expectedBonus, $user->balance);

        // Verify Voucher usage and count
        $this->assertEquals(1, VoucherUsage::count());
        $this->assertEquals(1, $voucher->refresh()->used_count);
    }
}
