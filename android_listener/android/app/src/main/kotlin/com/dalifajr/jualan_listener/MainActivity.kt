package com.dalifajr.jualan_listener

import android.content.ComponentName
import android.content.Intent
import android.provider.Settings
import androidx.annotation.NonNull
import com.dalifajr.jualan_listener.data.EventQueueStore
import com.dalifajr.jualan_listener.data.QueuedPaymentEvent
import com.dalifajr.jualan_listener.network.ListenerApiClient
import com.dalifajr.jualan_listener.worker.RetryScheduler
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

class MainActivity : FlutterActivity() {
	private val channelName = "jualan_listener/native"

	override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
		super.configureFlutterEngine(flutterEngine)

		MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
			.setMethodCallHandler { call, result ->
				when (call.method) {
					"isKeepAliveForegroundEnabled" -> {
						result.success(ListenerConfigStore.isKeepAliveForegroundEnabled(this))
					}

					"setKeepAliveForegroundEnabled" -> {
						val enabled = call.argument<Boolean>("enabled") ?: false
						try {
							ListenerConfigStore.setKeepAliveForegroundEnabled(this, enabled)
							if (enabled) {
								ListenerKeepAliveService.start(applicationContext)
							} else {
								ListenerKeepAliveService.stop(applicationContext)
							}
							result.success(true)
						} catch (e: Exception) {
							ListenerConfigStore.setKeepAliveForegroundEnabled(this, false)
							result.error(
								"KEEP_ALIVE_START_FAILED",
								e.message ?: "Gagal mengaktifkan notifikasi background",
								null,
							)
						}
					}

					"lockToRecommendedApps" -> {
						ListenerConfigStore.setConfig(
							this,
							ListenerConfigStore.getEndpoint(this),
							ListenerConfigStore.getEndpointSecondary(this),
							ListenerConfigStore.getSecret(this),
							false,
						)
						ListenerConfigStore.setSelectedApps(this, ListenerConfigStore.getDefaultSelectedApps())
						result.success(ListenerConfigStore.getDefaultSelectedApps().toList())
					}

					"openNotificationListenerSettings" -> {
						val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
						startActivity(intent)
						result.success(true)
					}

					"isListenerEnabled" -> {
						result.success(isNotificationListenerEnabled())
					}

					"getInstalledApps" -> {
						result.success(InstalledAppsProvider.listLaunchableApps(this))
					}

					"getConfig" -> {
						val payload = mapOf(
							"endpoint" to ListenerConfigStore.getEndpoint(this),
							"endpointSecondary" to ListenerConfigStore.getEndpointSecondary(this),
							"secret" to ListenerConfigStore.getSecret(this),
							"monitorAll" to ListenerConfigStore.isMonitorAll(this),
						)
						result.success(payload)
					}

					"setConfig" -> {
						val endpoint = call.argument<String>("endpoint").orEmpty()
						val endpointSecondary = call.argument<String>("endpointSecondary").orEmpty()
						val secret = call.argument<String>("secret").orEmpty()
						val monitorAll = call.argument<Boolean>("monitorAll") ?: true
						ListenerConfigStore.setConfig(this, endpoint, endpointSecondary, secret, monitorAll)
						RetryScheduler.enqueue(applicationContext)
						result.success(true)
					}

					"getSelectedApps" -> {
						result.success(ListenerConfigStore.getSelectedApps(this).toList())
					}

					"setSelectedApps" -> {
						val selected = call.argument<List<String>>("packageNames")?.toSet() ?: emptySet()
						ListenerConfigStore.setSelectedApps(this, selected)
						result.success(true)
					}

					"enqueueFlush" -> {
						RetryScheduler.enqueue(applicationContext)
						result.success(true)
					}

					"getPendingQueueCount" -> {
						CoroutineScope(Dispatchers.IO).launch {
							val count = EventQueueStore.pendingCount(applicationContext)
							withContext(Dispatchers.Main) {
								result.success(count)
							}
						}
					}

					"testConnectionNative" -> {
						val endpoint = call.argument<String>("endpoint").orEmpty()
						val secret = call.argument<String>("secret").orEmpty()
						CoroutineScope(Dispatchers.IO).launch {
							val response = ListenerApiClient.testConnection(endpoint, secret)
							withContext(Dispatchers.Main) {
								result.success(
									mapOf(
										"ok" to response.isSuccess,
										"statusCode" to response.statusCode,
										"body" to response.body,
										"error" to response.error,
									)
								)
							}
						}
					}

					"enqueueTestPayload" -> {
						val amount = (call.argument<Number>("amount")?.toLong()) ?: 0L
						val sourceApp = call.argument<String>("sourceApp").orEmpty().ifBlank { "TEST_APP" }
						val reference = call.argument<String>("reference")
						val rawText = call.argument<String>("rawText").orEmpty().ifBlank {
							"Pembayaran berhasil Rp$amount"
						}

						val endpoints = ListenerConfigStore.getActiveEndpoints(this)
						val secret = ListenerConfigStore.getSecret(this)
						if (endpoints.isEmpty() || secret.isBlank()) {
							result.error("CONFIG_EMPTY", "Endpoint/secret belum diatur", null)
						} else if (amount <= 0L) {
							result.error("INVALID_AMOUNT", "Amount harus > 0", null)
						} else {
							CoroutineScope(Dispatchers.IO).launch {
								val idempotencyKey = UUID.randomUUID().toString()
								val enqueued = endpoints.map { endpoint ->
									val event = QueuedPaymentEvent(
										id = UUID.randomUUID().toString(),
										idempotencyKey = idempotencyKey,
										endpoint = endpoint,
										secret = secret,
										amount = amount,
										sourceApp = sourceApp,
										reference = reference,
										rawText = rawText,
									)
									EventQueueStore.enqueue(applicationContext, event)
								}.any { it }

								if (enqueued) {
									RetryScheduler.enqueue(applicationContext)
								}

								withContext(Dispatchers.Main) {
									result.success(true)
								}
							}
						}
					}

					else -> result.notImplemented()
				}
			}
	}

	private fun isNotificationListenerEnabled(): Boolean {
		val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: return false
		val expected = ComponentName(this, PaymentNotificationListenerService::class.java).flattenToString()
		return flat.contains(expected)
	}
}
