package com.dalifajr.jualan_listener

object SupportedPaymentApps {
    // Keep this list explicit so listener scope stays narrow and predictable.
    private val exactPackages = setOf(
        "id.dana",
        "com.gojek.app",
        "com.gojek.gopay",
        "com.shopee.id",
        "com.shopeepay.id",
        "com.seabank.seabank",
        "id.co.bke.seabank",
    )

    private val containsFallback = listOf(
        "seabank",
        "gopay",
        "shopee",
        "shopeepay",
        "dana",
    )

    fun isSupported(packageName: String): Boolean {
        val normalized = packageName.trim().lowercase()
        if (normalized.isBlank()) return false
        if (normalized in exactPackages) return true
        return containsFallback.any { key -> normalized.contains(key) }
    }
}
