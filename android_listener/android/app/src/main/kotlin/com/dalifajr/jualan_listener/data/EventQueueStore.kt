package com.dalifajr.jualan_listener.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object EventQueueStore {
    private const val PREF_NAME = "listener_queue"
    private const val KEY_EVENTS = "events"

    @Synchronized
    fun enqueue(context: Context, event: QueuedPaymentEvent): Boolean {
        val events = load(context).toMutableList()
        val duplicate = events.any {
            it.idempotencyKey == event.idempotencyKey && it.endpoint == event.endpoint
        }
        if (duplicate) return false

        events.add(event)
        save(context, events)
        return true
    }

    @Synchronized
    fun dueEvents(context: Context, nowMillis: Long, limit: Int = 50): List<QueuedPaymentEvent> {
        return load(context)
            .asSequence()
            .filter { it.status == "pending" && it.nextAttemptAt <= nowMillis }
            .take(limit)
            .toList()
    }

    @Synchronized
    fun markSent(context: Context, id: String) {
        updateById(context, id) { it.copy(status = "sent", lastError = "") }
    }

    @Synchronized
    fun markRetry(context: Context, id: String, retryCount: Int, nextAttemptAt: Long, lastError: String) {
        updateById(context, id) {
            it.copy(
                status = "pending",
                retryCount = retryCount,
                nextAttemptAt = nextAttemptAt,
                lastError = lastError,
            )
        }
    }

    @Synchronized
    fun markDead(context: Context, id: String, lastError: String) {
        updateById(context, id) {
            it.copy(status = "dead", lastError = lastError)
        }
    }

    @Synchronized
    fun pendingCount(context: Context): Int {
        return load(context).count { it.status == "pending" }
    }

    @Synchronized
    private fun updateById(
        context: Context,
        id: String,
        transformer: (QueuedPaymentEvent) -> QueuedPaymentEvent,
    ) {
        val updated = load(context).map { event ->
            if (event.id == id) transformer(event) else event
        }
        save(context, updated)
    }

    private fun load(context: Context): List<QueuedPaymentEvent> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_EVENTS, "[]") ?: "[]"
        val arr = JSONArray(raw)
        val result = mutableListOf<QueuedPaymentEvent>()

        for (idx in 0 until arr.length()) {
            val item = arr.optJSONObject(idx) ?: continue
            result.add(item.toEvent())
        }
        return result
    }

    private fun save(context: Context, events: List<QueuedPaymentEvent>) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val arr = JSONArray()
        events.forEach { arr.put(it.toJson()) }
        prefs.edit().putString(KEY_EVENTS, arr.toString()).apply()
    }

    private fun JSONObject.toEvent(): QueuedPaymentEvent {
        return QueuedPaymentEvent(
            id = optString("id"),
            idempotencyKey = optString("idempotency_key"),
            endpoint = optString("endpoint"),
            secret = optString("secret"),
            amount = optLong("amount"),
            sourceApp = optString("source_app"),
            reference = if (isNull("reference")) null else optString("reference"),
            rawText = optString("raw_text"),
            status = optString("status", "pending"),
            retryCount = optInt("retry_count", 0),
            nextAttemptAt = optLong("next_attempt_at", System.currentTimeMillis()),
            lastError = optString("last_error", ""),
            createdAt = optLong("created_at", System.currentTimeMillis()),
        )
    }

    private fun QueuedPaymentEvent.toJson(): JSONObject {
        return JSONObject().apply {
            put("id", id)
            put("idempotency_key", idempotencyKey)
            put("endpoint", endpoint)
            put("secret", secret)
            put("amount", amount)
            put("source_app", sourceApp)
            put("reference", reference)
            put("raw_text", rawText)
            put("status", status)
            put("retry_count", retryCount)
            put("next_attempt_at", nextAttemptAt)
            put("last_error", lastError)
            put("created_at", createdAt)
        }
    }
}
