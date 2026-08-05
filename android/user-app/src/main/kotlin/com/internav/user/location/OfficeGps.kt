package com.internav.user.location

import com.internav.shared.local.CachedCellEntity
import kotlin.math.cos

// Calibration reference: the user was standing in cell 126 at these GPS coordinates.
const val REF_LAT = -33.578835
const val REF_LNG = -70.578842

// Cell 126 is the calibration cell. It sits at the same plan position on both floors
// (both plans are identical 2000x3000), so one anchor works for every floor.
const val CALIBRATION_CELL_NUMBER = 126

// Real-world scale measured by the user: 3.25 cells = 2 meters.
private const val CELLS_PER_2_METERS = 3.25
private const val CELL_SIZE_UNITS = 100
private const val UNITS_PER_METER = CELL_SIZE_UNITS * CELLS_PER_2_METERS / 2.0

private const val METERS_PER_DEGREE_LAT = 111320.0
private val METERS_PER_DEGREE_LNG = METERS_PER_DEGREE_LAT * cos(Math.toRadians(REF_LAT))

data class PlanPoint(val x: Float, val y: Float)

fun gpsToPlan(
    lat: Double,
    lng: Double,
    planWidth: Int,
    planHeight: Int,
    anchor: PlanPoint
): PlanPoint {
    val unitsPerDegLat = UNITS_PER_METER * METERS_PER_DEGREE_LAT
    val unitsPerDegLng = UNITS_PER_METER * METERS_PER_DEGREE_LNG
    val x = ((REF_LNG - lng) * unitsPerDegLng + anchor.x.toDouble()).toFloat()
    val y = ((lat - REF_LAT) * unitsPerDegLat + anchor.y.toDouble()).toFloat()
    return PlanPoint(x, y)
}

fun isInsidePlan(pt: PlanPoint, planWidth: Int, planHeight: Int): Boolean =
    pt.x >= 0f && pt.x <= planWidth.toFloat() && pt.y >= 0f && pt.y <= planHeight.toFloat()

fun findCellCenter(cells: List<CachedCellEntity>, cellNumber: Int): PlanPoint? {
    val nCols = cells.maxOfOrNull { it.column }?.plus(1) ?: 0
    if (nCols <= 0) return null
    val cell = cells.firstOrNull { it.row * nCols + it.column + 1 == cellNumber } ?: return null
    return PlanPoint(cell.centerX.toFloat(), cell.centerY.toFloat())
}
