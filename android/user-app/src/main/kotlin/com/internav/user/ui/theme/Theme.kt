package com.internav.user.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF16A34A),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCFCE7),
    secondary = Color(0xFF64748B),
    surface = Color.White,
    background = Color(0xFFF5F6FA),
    error = Color(0xFFDC2626)
)

@Composable
fun UserAppTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content
    )
}
