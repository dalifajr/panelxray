package com.dalifajr.jualan_listener

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.dalifajr.jualan_listener.worker.RetryScheduler

class BootCompletedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action == Intent.ACTION_BOOT_COMPLETED) {
            RetryScheduler.enqueue(context.applicationContext)
            if (ListenerConfigStore.isKeepAliveForegroundEnabled(context.applicationContext)) {
                ListenerKeepAliveService.start(context.applicationContext)
            }
        }
    }
}
