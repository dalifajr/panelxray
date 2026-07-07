<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('telegram_bot_users', function (Blueprint $table) {
            $table->id();
            $table->string('tg_id')->unique();
            $table->string('tg_username')->default('');
            $table->string('tg_full_name')->default('');
            $table->string('role')->default('user');       // admin, reseller, user
            $table->string('status')->default('pending');  // pending, approved, rejected, suspended, kicked
            $table->string('note')->default('');
            $table->integer('ssh_limit')->default(0);      // 0 = unlimited
            $table->integer('xray_limit')->default(0);     // 0 = unlimited
            $table->foreignId('user_id')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamps();
        });

        Schema::create('telegram_access_requests', function (Blueprint $table) {
            $table->id();
            $table->string('tg_id');
            $table->string('tg_username')->default('');
            $table->string('tg_full_name')->default('');
            $table->text('reason')->nullable();
            $table->string('status')->default('pending'); // pending, approved, rejected
            $table->string('admin_id')->default('');
            $table->text('admin_reason')->nullable();
            $table->timestamp('processed_at')->nullable();
            $table->timestamps();
        });

        Schema::create('telegram_quota_requests', function (Blueprint $table) {
            $table->id();
            $table->string('tg_id');
            $table->text('reason')->nullable();
            $table->string('status')->default('pending');
            $table->string('admin_id')->default('');
            $table->text('admin_reason')->nullable();
            $table->timestamp('processed_at')->nullable();
            $table->timestamps();
        });

        Schema::create('telegram_account_registry', function (Blueprint $table) {
            $table->id();
            $table->string('tg_id');
            $table->string('service');     // ssh, vmess, vless, trojan, shadowsocks
            $table->string('category');    // create, renew
            $table->string('username');
            $table->string('expires_at')->default('');
            $table->boolean('is_trial')->default(false);
            $table->boolean('active')->default(true);
            $table->timestamps();

            $table->index(['tg_id', 'category', 'service']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('telegram_account_registry');
        Schema::dropIfExists('telegram_quota_requests');
        Schema::dropIfExists('telegram_access_requests');
        Schema::dropIfExists('telegram_bot_users');
    }
};
