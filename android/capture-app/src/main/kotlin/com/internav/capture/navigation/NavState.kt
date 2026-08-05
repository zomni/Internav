package com.internav.capture.navigation

import androidx.compose.runtime.mutableStateListOf

object NavState {
    val crumbs = mutableStateListOf<String>()

    fun pop() {
        if (crumbs.isNotEmpty()) crumbs.removeAt(crumbs.lastIndex)
    }

    fun clear() {
        crumbs.clear()
    }
}
