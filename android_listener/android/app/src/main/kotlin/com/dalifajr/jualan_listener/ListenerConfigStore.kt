package com.dalifajr.jualan_listener

import android.content.Context

object ListenerConfigStore {
    private const val PREF_NAME = "listener_config"
    private const val KEY_ENDPOINT = "endpoint"
    private const val KEY_ENDPOINT_SECONDARY = "endpoint_secondary"
    private const val KEY_SECRET = "secret"
    private const val KEY_MONITOR_ALL = "monitor_all"
    private const val KEY_SELECTED_APPS = "selected_apps"
    private const val KEY_KEEP_ALIVE_FOREGROUND = "keep_alive_foreground"

    private val defaultPaymentPackages = setOf(
        "id.dana",
        "com.gojek.app",
        "com.gojek.gopay",
        "com.shopee.id",
        "com.shopeepay.id",
    )

    fun getEndpoint(context: Context): String =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getString(KEY_ENDPOINT, "")
            .orEmpty()

    fun getEndpointSecondary(context: Context): String =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getString(KEY_ENDPOINT_SECONDARY, "")
            .orEmpty()

    fun getSecret(context: Context): String =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getString(KEY_SECRET, "")
            .orEmpty()

    fun isMonitorAll(context: Context): Boolean =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_MONITOR_ALL, false)

    fun getSelectedApps(context: Context): Set<String> =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getStringSet(KEY_SELECTED_APPS, defaultPaymentPackages)
            ?.toSet()
            ?: defaultPaymentPackages

    fun getDefaultSelectedApps(): Set<String> = defaultPaymentPackages

    fun isKeepAliveForegroundEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_KEEP_ALIVE_FOREGROUND, false)

    fun setKeepAliveForegroundEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_KEEP_ALIVE_FOREGROUND, enabled)
            .apply()
    }

    fun setConfig(
        context: Context,
        endpoint: String,
        endpointSecondary: String,
        secret: String,
        monitorAll: Boolean,
    ) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_ENDPOINT, endpoint.trim())
            .putString(KEY_ENDPOINT_SECONDARY, endpointSecondary.trim())
            .putString(KEY_SECRET, secret.trim())
            .putBoolean(KEY_MONITOR_ALL, monitorAll)
            .apply()
    }

    fun getActiveEndpoints(context: Context): List<String> {
        return listOf(getEndpoint(context), getEndpointSecondary(context))
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .distinct()
    }

    fun setSelectedApps(context: Context, packageNames: Set<String>) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit()
            .putStringSet(KEY_SELECTED_APPS, packageNames)
            .apply()
    }
}
