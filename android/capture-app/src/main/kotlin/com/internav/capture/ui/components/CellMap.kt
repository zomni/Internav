package com.internav.capture.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.internav.capture.ui.utils.cellCaptureColor
import com.internav.capture.ui.utils.cellNumber
import com.internav.shared.model.Cell
import com.internav.shared.model.FloorPlan
import kotlin.math.max
import kotlin.math.min

private val WALKABLE_COLOR = Color(0x6622C55E)
private val BLOCKED_COLOR = Color(0x6690A4AE)
private val SELECTED_COLOR = Color(0xFF16A34A)
private val PRESSED_COLOR = Color(0xAA22C55E)
private val MIN_LABEL_WIDTH_PX = 28f

private const val MIN_SCALE = 1f
private const val MAX_SCALE = 5f
private const val PRESS_DURATION_MS = 300L

@androidx.compose.runtime.Composable
fun CellMap(
    plan: FloorPlan,
    planImage: ImageBitmap?,
    gridCellSize: Float,
    cells: List<Cell>,
    selectedCellId: String? = null,
    onCellTap: ((Cell) -> Unit)? = null,
    captureCounts: Map<String, Int> = emptyMap(),
    modifier: Modifier = Modifier
) {
    var viewSize by remember { mutableStateOf(IntSize.Zero) }
    val textMeasurer = rememberTextMeasurer()
    val density = LocalDensity.current.density

    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    var pressedCellId by remember { mutableStateOf<String?>(null) }

    val transformState = rememberTransformableState { zoomChange, panChange, _ ->
        scale = max(MIN_SCALE, min(MAX_SCALE, scale * zoomChange))
        if (scale > MIN_SCALE) {
            offset = Offset(
                x = offset.x + panChange.x,
                y = offset.y + panChange.y
            )
        } else {
            offset = Offset.Zero
        }
    }

    LaunchedEffect(pressedCellId) {
        if (pressedCellId != null) {
            kotlinx.coroutines.delay(PRESS_DURATION_MS)
            pressedCellId = null
        }
    }

    Canvas(
        modifier = modifier
            .aspectRatio(plan.width.toFloat() / plan.height)
            .onSizeChanged { viewSize = it }
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationX = offset.x
                translationY = offset.y
            }
            .transformable(state = transformState)
            .pointerInput(plan.id, cells, onCellTap) {
                detectTapGestures { offset ->
                    if (onCellTap == null) return@detectTapGestures
                    val sx = size.width.toFloat() / plan.width
                    val sy = size.height.toFloat() / plan.height
                    val px = offset.x / sx
                    val py = offset.y / sy
                    val hit = cells.firstOrNull { c ->
                        val left = c.column * gridCellSize
                        val top = c.row * gridCellSize
                        px >= left && px < left + gridCellSize && py >= top && py < top + gridCellSize
                    }
                    if (hit != null) {
                        pressedCellId = hit.id
                        onCellTap(hit)
                    }
                }
            }
    ) {
        if (planImage != null) {
            drawImage(
                image = planImage,
                dstOffset = IntOffset.Zero,
                dstSize = IntSize(size.width.toInt(), size.height.toInt())
            )
        }
        if (viewSize.width == 0 || viewSize.height == 0) return@Canvas
        val sx = size.width.toFloat() / plan.width
        val sy = size.height.toFloat() / plan.height
        cells.forEach { c ->
            val left = c.column * gridCellSize * sx
            val top = c.row * gridCellSize * sy
            val w = gridCellSize * sx
            val h = gridCellSize * sy
            val isSelected = c.id == selectedCellId
            val isPressed = c.id == pressedCellId
            val color = when {
                isPressed -> PRESSED_COLOR
                isSelected -> SELECTED_COLOR
                c.walkable -> WALKABLE_COLOR
                else -> BLOCKED_COLOR
            }
            drawRect(color, topLeft = Offset(left, top), size = Size(w, h))
            if (isSelected) {
                drawRect(
                    Color.White,
                    topLeft = Offset(left, top),
                    size = Size(w, h),
                    style = Stroke(width = 2.dp.toPx())
                )
            }
            if (w >= MIN_LABEL_WIDTH_PX) {
                val number = cellNumber(c, cells)
                if (number > 0) {
                    val fontSize = (w * 0.35f / density).sp
                    val count = captureCounts[c.id] ?: 0
                    val textColor = cellCaptureColor(count)
                    val layout = textMeasurer.measure(
                        AnnotatedString("#$number"),
                        style = TextStyle(fontSize = fontSize, fontWeight = FontWeight.Bold, color = textColor)
                    )
                    drawText(
                        layout,
                        topLeft = Offset(
                            left + (w - layout.size.width) / 2f,
                            top + (h - layout.size.height) / 2f
                        )
                    )
                }
            }
        }
    }
}
