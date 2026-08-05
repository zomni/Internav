package com.internav.capture.ui.utils

import androidx.compose.ui.graphics.Color
import com.internav.shared.model.Cell
import kotlin.math.roundToInt

fun cellNumber(cell: Cell, cells: List<Cell>): Int {
    val nCols = cells.maxOfOrNull { it.column }?.plus(1) ?: 0
    return if (nCols > 0) cell.row * nCols + cell.column + 1 else 0
}

fun cellLabel(cell: Cell, cells: List<Cell>): String =
    "#${cellNumber(cell, cells)} (${cell.row},${cell.column})"

fun cellCaptureColor(count: Int): Color {
    if (count <= 0) return Color(0xCCDC2626)
    if (count >= 10) return Color(0xCC16A34A)
    val t = count / 10f
    val r = lerp(0xDC, 0x16, t)
    val g = lerp(0x26, 0xA3, t)
    val b = lerp(0x26, 0x4A, t)
    return Color(r, g, b)
}

private fun lerp(from: Int, to: Int, t: Float): Int =
    (from + (to - from) * t).roundToInt()
