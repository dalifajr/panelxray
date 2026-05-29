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
        Schema::create('transactions', function (Blueprint $table) {
            $table->id();
            $table->string('reference')->unique();
            $table->foreignId('user_id')->constrained('users')->onDelete('cascade');
            $table->string('type'); // topup, vpn_purchase
            $table->integer('amount');
            $table->integer('unique_code')->default(0);
            $table->integer('total_amount');
            $table->string('status')->default('pending'); // pending, success, cancelled, failed
            $table->text('description')->nullable();
            $table->json('metadata')->nullable(); // to store VPN purchase details like protocol, username, etc.
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('transactions');
    }
};
