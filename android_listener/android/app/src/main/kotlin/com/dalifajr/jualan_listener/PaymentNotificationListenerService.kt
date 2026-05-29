package com.dalifajr.jualan_listener

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.dalifajr.jualan_listener.data.EventQueueStore
import com.dalifajr.jualan_listener.data.QueuedPaymentEvent
import com.dalifajr.jualan_listener.utils.NotificationTextExtractor
import com.dalifajr.jualan_listener.utils.RupiahParser
import com.dalifajr.jualan_listener.worker.RetryScheduler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.UUID

class PaymentNotificationListenerService : NotificationListenerService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null) return

        val endpoints = ListenerConfigStore.getActiveEndpoints(this)
        val secret = ListenerConfigStore.getSecret(this)
        if (endpoints.isEmpty() || secret.isBlank()) {
            return
        }

        val packageName = sbn.packageName.orEmpty()
        if (!SupportedPaymentApps.isSupported(packageName)) {
            return
        }

        val monitorAll = ListenerConfigStore.isMonitorAll(this)
        val selectedApps = ListenerConfigStore.getSelectedApps(this)
        if (!monitorAll && packageName !in selectedApps) {
            return
        }

        val rawText = NotificationTextExtractor.extract(sbn.notification)
        if (rawText.isBlank()) {
            return
        }

        val amount = RupiahParser.parseAmount(rawText) ?: return
        if (amount <= 0) return

        val reference = NotificationTextExtractor.extractReference(rawText)
        val idempotencyKey = UUID.randomUUID().toString()

        scope.launch {
            var enqueued = false
            endpoints.forEach { endpoint ->
                val event = QueuedPaymentEvent(
                    id = UUID.randomUUID().toString(),
                    idempotencyKey = idempotencyKey,
                    endpoint = endpoint,
                    secret = secret,
                    amount = amount,
                    sourceApp = packageName,
                    reference = reference,
                    rawText = rawText,
                )
                if (EventQueueStore.enqueue(applicationContext, event)) {
                    enqueued = true
                }
            }
            if (enqueued) {
                RetryScheduler.enqueue(applicationContext)
            }
        }
    }
}
