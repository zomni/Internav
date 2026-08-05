package com.internav.capture.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF2563EB),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDBEAFE),
    secondary = Color(0xFF64748B),
    surface = Color.White,
    background = Color(0xFFF5F6FA),
    error = Color(0xFFDC2626)
)

@Composable
fun CaptureAppTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content
    )
}
