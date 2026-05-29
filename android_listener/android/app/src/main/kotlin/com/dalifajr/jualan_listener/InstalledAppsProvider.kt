package com.dalifajr.jualan_listener

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager

object InstalledAppsProvider {
    fun listLaunchableApps(context: Context): List<Map<String, String>> {
        val pm = context.packageManager
        val intent = Intent(Intent.ACTION_MAIN, null).apply {
            addCategory(Intent.CATEGORY_LAUNCHER)
        }

        val seen = mutableSetOf<String>()
        val result = pm.queryIntentActivities(intent, PackageManager.MATCH_ALL)
            .asSequence()
            .filter { it.activityInfo?.packageName != null }
            .mapNotNull { info ->
                val packageName = info.activityInfo.packageName ?: return@mapNotNull null
                if (!seen.add(packageName)) return@mapNotNull null

                val label = info.loadLabel(pm)?.toString().orEmpty().ifBlank { packageName }
                mapOf(
                    "packageName" to packageName,
                    "label" to label,
                )
            }
            .sortedBy { it["label"]?.lowercase().orEmpty() }
            .toList()

        return result
    }
}
