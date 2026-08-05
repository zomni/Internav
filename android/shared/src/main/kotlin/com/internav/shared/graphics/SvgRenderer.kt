package com.internav.shared.graphics

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import androidx.core.graphics.PathParser
import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import kotlin.math.max

private const val MAX_RENDER_DIM = 1024

private data class SvgRect(
    val x: Float,
    val y: Float,
    val w: Float,
    val h: Float,
    val fill: Int?,
    val stroke: Int?,
    val strokeWidth: Float
)

private data class SvgPath(
    val d: String,
    val fill: Int?,
    val stroke: Int?,
    val strokeWidth: Float
)

fun decodeFloorPlanImage(bytes: ByteArray): Bitmap? {
    try {
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.let { return it }
    } catch (_: Exception) { }
    return renderSvg(bytes)
}

private fun parseColor(value: String?): Int? {
    if (value.isNullOrBlank() || value.equals("none", ignoreCase = true)) return null
    val v = value.trim()
    if (v.startsWith("#")) {
        val hex = v.removePrefix("#")
        return try {
            when (hex.length) {
                3 -> Color.rgb(
                    hex[0].digitToInt(16) * 17,
                    hex[1].digitToInt(16) * 17,
                    hex[2].digitToInt(16) * 17
                )
                6 -> Color.parseColor("#$hex")
                else -> null
            }
        } catch (_: IllegalArgumentException) {
            null
        }
    }
    return when (v.lowercase()) {
        "black" -> Color.BLACK
        "white" -> Color.WHITE
        "gray", "grey" -> Color.GRAY
        "red" -> Color.RED
        "green" -> Color.GREEN
        "blue" -> Color.BLUE
        else -> null
    }
}

private fun toFloat(value: String?): Float? = value?.toFloatOrNull()

fun renderSvg(svgBytes: ByteArray): Bitmap? {
    return try {
        val parser = XmlPullParserFactory.newInstance().newPullParser()
        parser.setInput(svgBytes.inputStream(), null)

        var vbX = 0f
        var vbY = 0f
        var vbW = 0f
        var vbH = 0f
        var hasViewBox = false

        val rects = mutableListOf<SvgRect>()
        val paths = mutableListOf<SvgPath>()

        var event = parser.eventType
        while (event != XmlPullParser.END_DOCUMENT) {
            if (event == XmlPullParser.START_TAG) {
                when (parser.name) {
                    "svg" -> {
                        val w = toFloat(parser.getAttributeValue(null, "width"))
                        val h = toFloat(parser.getAttributeValue(null, "height"))
                        if (w != null && h != null && w > 0 && h > 0) {
                            vbW = w
                            vbH = h
                            hasViewBox = true
                        }
                        parser.getAttributeValue(null, "viewBox")?.let { vb ->
                            val parts = vb.trim().split(Regex("[\\s,]+")).mapNotNull { it.toFloatOrNull() }
                            if (parts.size >= 4 && parts[2] > 0 && parts[3] > 0) {
                                vbX = parts[0]
                                vbY = parts[1]
                                vbW = parts[2]
                                vbH = parts[3]
                                hasViewBox = true
                            }
                        }
                    }
                    "rect" -> {
                        val x = toFloat(parser.getAttributeValue(null, "x")) ?: 0f
                        val y = toFloat(parser.getAttributeValue(null, "y")) ?: 0f
                        val w = toFloat(parser.getAttributeValue(null, "width")) ?: 0f
                        val h = toFloat(parser.getAttributeValue(null, "height")) ?: 0f
                        val fill = parseColor(parser.getAttributeValue(null, "fill"))
                        val stroke = parseColor(parser.getAttributeValue(null, "stroke"))
                        val sw = toFloat(parser.getAttributeValue(null, "stroke-width")) ?: 1f
                        rects += SvgRect(x, y, w, h, fill, stroke, sw)
                    }
                    "path" -> {
                        val d = parser.getAttributeValue(null, "d") ?: ""
                        val fill = parseColor(parser.getAttributeValue(null, "fill"))
                        val stroke = parseColor(parser.getAttributeValue(null, "stroke"))
                        val sw = toFloat(parser.getAttributeValue(null, "stroke-width")) ?: 1f
                        paths += SvgPath(d, fill, stroke, sw)
                    }
                }
            }
            event = parser.next()
        }

        if (!hasViewBox || vbW <= 0 || vbH <= 0) return null

        val scale = minOf(MAX_RENDER_DIM / vbW, MAX_RENDER_DIM / vbH)
        val targetW = (vbW * scale).toInt().coerceAtLeast(1)
        val targetH = (vbH * scale).toInt().coerceAtLeast(1)
        val sx = targetW / vbW
        val sy = targetH / vbH
        val avgScale = (sx + sy) / 2f

        val bitmap = Bitmap.createBitmap(targetW, targetH, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
        val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeCap = Paint.Cap.ROUND
            strokeJoin = Paint.Join.ROUND
        }

        for (r in rects) {
            val rect = RectF(
                (r.x - vbX) * sx,
                (r.y - vbY) * sy,
                (r.x + r.w - vbX) * sx,
                (r.y + r.h - vbY) * sy
            )
            r.fill?.let { color ->
                fillPaint.color = color
                canvas.drawRect(rect, fillPaint)
            }
            r.stroke?.let { color ->
                strokePaint.color = color
                strokePaint.strokeWidth = max(1f, r.strokeWidth * avgScale)
                canvas.drawRect(rect, strokePaint)
            }
        }

        val matrix = Matrix().apply {
            postScale(sx, sy)
            postTranslate(-vbX * sx, -vbY * sy)
        }

        for (p in paths) {
            val path = try {
                PathParser.createPathFromPathData(p.d)
            } catch (_: Exception) {
                continue
            }
            path.transform(matrix)
            p.fill?.let { color ->
                fillPaint.color = color
                canvas.drawPath(path, fillPaint)
            }
            p.stroke?.let { color ->
                strokePaint.color = color
                strokePaint.strokeWidth = max(1f, p.strokeWidth * avgScale)
                canvas.drawPath(path, strokePaint)
            }
        }

        bitmap
    } catch (_: Exception) {
        null
    }
}
