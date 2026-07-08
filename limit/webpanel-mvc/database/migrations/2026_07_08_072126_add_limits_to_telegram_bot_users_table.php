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
        Schema::table('telegram_bot_users', function (Blueprint $table) {
            if (!Schema::hasColumn('telegram_bot_users', 'ssh_limit')) {
                $table->integer('ssh_limit')->default(0)->after('note');
            }
            if (!Schema::hasColumn('telegram_bot_users', 'xray_limit')) {
                $table->integer('xray_limit')->default(0)->after('ssh_limit');
            }
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('telegram_bot_users', function (Blueprint $table) {
            if (Schema::hasColumn('telegram_bot_users', 'ssh_limit')) {
                $table->dropColumn('ssh_limit');
            }
            if (Schema::hasColumn('telegram_bot_users', 'xray_limit')) {
                $table->dropColumn('xray_limit');
            }
        });
    }
};
