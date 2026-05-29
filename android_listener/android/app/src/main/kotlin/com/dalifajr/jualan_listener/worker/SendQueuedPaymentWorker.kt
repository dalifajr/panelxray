package com.dalifajr.jualan_listener.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.dalifajr.jualan_listener.data.EventQueueStore
import com.dalifajr.jualan_listener.network.ListenerApiClient
import kotlin.math.min
import kotlin.math.pow

class SendQueuedPaymentWorker(
    context: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        val now = System.currentTimeMillis()
        val dueEvents = EventQueueStore.dueEvents(applicationContext, nowMillis = now, limit = 50)

        if (dueEvents.isEmpty()) {
            return Result.success()
        }

        for (event in dueEvents) {
            val result = ListenerApiClient.sendPaymentEvent(event)
            if (result.isSuccess) {
                EventQueueStore.markSent(applicationContext, event.id)
                continue
            }

            if (!result.shouldRetry) {
                EventQueueStore.markDead(applicationContext, event.id, result.error)
                continue
            }

            val nextRetryCount = event.retryCount + 1
            val delaySeconds = min(8 * 60 * 60.0, (2.0.pow(nextRetryCount.toDouble()) * 30.0)).toLong()
            val nextAttempt = System.currentTimeMillis() + (delaySeconds * 1000L)

            if (nextRetryCount > 12) {
                EventQueueStore.markDead(applicationContext, event.id, "Maks retry tercapai: ${result.error}")
            } else {
                EventQueueStore.markRetry(
                    applicationContext,
                    id = event.id,
                    retryCount = nextRetryCount,
                    nextAttemptAt = nextAttempt,
                    lastError = result.error,
                )
            }
        }

        val remaining = EventQueueStore.pendingCount(applicationContext)
        if (remaining > 0) {
            RetryScheduler.enqueue(applicationContext)
        }

        return Result.success()
    }
}
