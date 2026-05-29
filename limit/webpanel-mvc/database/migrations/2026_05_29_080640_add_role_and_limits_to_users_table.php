<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('username')->unique()->after('id')->nullable();
            $table->string('role')->default('customer')->after('password'); // admin or customer
            $table->string('status')->default('active')->after('role'); // active or suspended
            $table->integer('vpn_account_limit')->default(2)->after('status');
            $table->string('telegram_id')->unique()->nullable()->after('vpn_account_limit');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn(['username', 'role', 'status', 'vpn_account_limit', 'telegram_id']);
        });
    }
};
