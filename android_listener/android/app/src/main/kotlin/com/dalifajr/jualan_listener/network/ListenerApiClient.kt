package com.dalifajr.jualan_listener.network

import com.dalifajr.jualan_listener.data.QueuedPaymentEvent
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object ListenerApiClient {
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    data class SendResult(
        val isSuccess: Boolean,
        val shouldRetry: Boolean,
        val error: String,
        val statusCode: Int,
        val body: String,
    )

    fun sendPaymentEvent(event: QueuedPaymentEvent): SendResult {
        return try {
            val timestamp = (System.currentTimeMillis() / 1000L).toString()
            val payload = JSONObject().apply {
                put("amount", event.amount)
                put("source_app", event.sourceApp)
                put("reference", event.reference)
                put("raw_text", event.rawText)
                put("metadata", JSONObject().apply {
                    put("from", "android_listener")
                })
            }

            val bodyString = payload.toString()
            val signature = buildSignature(event.secret, timestamp, bodyString)
            val request = Request.Builder()
                .url(event.endpoint)
                .addHeader("Content-Type", "application/json")
                .addHeader("X-Timestamp", timestamp)
                .addHeader("X-Signature", signature)
                .addHeader("X-Idempotency-Key", event.idempotencyKey)
                .post(bodyString.toRequestBody(jsonMediaType))
                .build()

            httpClient.newCall(request).execute().use { response ->
                val responseBody = response.body?.string().orEmpty()
                if (response.isSuccessful) {
                    return SendResult(
                        isSuccess = true,
                        shouldRetry = false,
                        error = "",
                        statusCode = response.code,
                        body = responseBody,
                    )
                }

                val shouldRetry = response.code >= 500 || response.code == 429
                SendResult(
                    isSuccess = false,
                    shouldRetry = shouldRetry,
                    error = "HTTP ${response.code}: $responseBody",
                    statusCode = response.code,
                    body = responseBody,
                )
            }
        } catch (e: Exception) {
            SendResult(
                isSuccess = false,
                shouldRetry = true,
                error = e.message ?: "unknown error",
                statusCode = 0,
                body = "",
            )
        }
    }

    fun testConnection(endpoint: String, secret: String): SendResult {
        return try {
            val timestamp = (System.currentTimeMillis() / 1000L).toString()
            val testEndpoint = when {
                endpoint.endsWith("/listener/payment") -> endpoint.replace("/listener/payment", "/listener/test-connection")
                endpoint.endsWith("/payment") -> endpoint.replace("/payment", "/test-connection")
                else -> endpoint.trimEnd('/') + "/listener/test-connection"
            }
            val payload = JSONObject().apply {
                put("device_id", "android-device")
                put("app_version", "0.1.0")
            }
            val bodyString = payload.toString()
            val signature = buildSignature(secret, timestamp, bodyString)
            val request = Request.Builder()
                .url(testEndpoint)
                .addHeader("Content-Type", "application/json")
                .addHeader("X-Timestamp", timestamp)
                .addHeader("X-Signature", signature)
                .addHeader("X-Idempotency-Key", "test-${System.currentTimeMillis()}")
                .post(bodyString.toRequestBody(jsonMediaType))
                .build()

            httpClient.newCall(request).execute().use { response ->
                val responseBody = response.body?.string().orEmpty()
                SendResult(
                    isSuccess = response.isSuccessful,
                    shouldRetry = false,
                    error = if (response.isSuccessful) "" else "HTTP ${response.code}: $responseBody",
                    statusCode = response.code,
                    body = responseBody,
                )
            }
        } catch (e: Exception) {
            SendResult(
                isSuccess = false,
                shouldRetry = false,
                error = e.message ?: "unknown error",
                statusCode = 0,
                body = "",
            )
        }
    }

    private fun buildSignature(secret: String, timestamp: String, body: String): String {
        val data = "$timestamp.$body".toByteArray(Charsets.UTF_8)
        val key = SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256")
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(key)
        val bytes = mac.doFinal(data)
        return bytes.joinToString("") { byte -> "%02x".format(byte) }
    }
}
