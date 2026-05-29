package com.dalifajr.jualan_listener.data

data class QueuedPaymentEvent(
    val id: String,
    val idempotencyKey: String,
    val endpoint: String,
    val secret: String,
    val amount: Long,
    val sourceApp: String,
    val reference: String?,
    val rawText: String,
    val status: String = "pending",
    val retryCount: Int = 0,
    val nextAttemptAt: Long = System.currentTimeMillis(),
    val lastError: String = "",
    val createdAt: Long = System.currentTimeMillis(),
)
