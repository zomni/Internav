package com.internav.capture.ui.utils

import android.content.Context
import android.content.SharedPreferences

object WifiScanThrottle {
    private const val SCAN_BUDGET = 4
    private const val SCAN_WINDOW_MS = 120_000L
    private const val PREFS_NAME = "internav_prefs"
    private const val KEY_TIMESTAMPS = "wifi_scan_timestamps"

    private var timestamps: MutableList<Long> = mutableListOf()
    private var loaded = false
    private var prefs: SharedPreferences? = null

    fun attach(context: Context) {
        if (loaded) return
        prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val raw = prefs?.getString(KEY_TIMESTAMPS, null)
        if (raw != null) {
            timestamps = raw.split(',').mapNotNull { it.toLongOrNull() }.toMutableList()
        }
        loaded = true
    }

    fun budget(): Int = SCAN_BUDGET

    fun windowMs(): Long = SCAN_WINDOW_MS

    fun recordScan(now: Long) {
        prune(now)
        timestamps.add(now)
        persist()
    }

    fun waitMsUntilAllowed(now: Long): Long {
        prune(now)
        if (timestamps.size < SCAN_BUDGET) return 0L
        val oldest = timestamps.minOrNull() ?: return 0L
        return (oldest + SCAN_WINDOW_MS - now).coerceAtLeast(0L)
    }

    private fun prune(now: Long) {
        timestamps.removeAll { now - it >= SCAN_WINDOW_MS }
    }

    private fun persist() {
        prefs?.edit()?.putString(KEY_TIMESTAMPS, timestamps.joinToString(","))?.apply()
    }
}
