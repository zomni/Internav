package com.internav.user.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CenterFocusStrong
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.internav.shared.api.ApiClient
import com.internav.shared.graphics.decodeFloorPlanImage
import com.internav.user.location.CALIBRATION_CELL_NUMBER
import com.internav.user.location.findCellCenter
import com.internav.user.location.gpsToPlan
import com.internav.user.location.isInsidePlan
import com.internav.user.viewmodel.MapViewModel
import com.internav.user.viewmodel.PositionSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.max
import kotlin.math.min

private const val MIN_SCALE = 1f
private const val MAX_SCALE = 5f

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MapScreen(
    buildingId: String,
    onBack: () -> Unit,
    viewModel: MapViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    var planImage by remember { mutableStateOf<ImageBitmap?>(null) }
    var permissionGranted by remember { mutableStateOf(
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
    ) }

    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }

    val gpsAnchor = remember(state.cells) {
        findCellCenter(state.cells, CALIBRATION_CELL_NUMBER)
    }

    val gpsPlanPt = if (state.positionSource == PositionSource.GPS) {
        gpsAnchor?.let { a ->
            state.gpsPosition?.let { g ->
                state.floorPlan?.let { p -> gpsToPlan(g.lat, g.lng, p.width, p.height, a) }
            }
        }
    } else null
    val gpsOutside = gpsPlanPt?.let { pt ->
        state.floorPlan?.let { p -> !isInsidePlan(pt, p.width, p.height) }
    } ?: false

    LaunchedEffect(buildingId) { viewModel.initialize(buildingId) }

    LaunchedEffect(state.floorPlan?.id) {
        val plan = state.floorPlan ?: return@LaunchedEffect
        planImage = null
        try {
            val imgResp = withContext(Dispatchers.IO) {
                ApiClient.getService().downloadFloorPlanImage(plan.id)
            }
            if (imgResp.isSuccessful) {
                val bmp = withContext(Dispatchers.IO) {
                    imgResp.body()?.bytes()?.let { decodeFloorPlanImage(it) }
                }
                if (bmp != null) planImage = bmp.asImageBitmap()
            }
        } catch (_: Exception) {
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        permissionGranted = granted
        if (granted) viewModel.startScanning()
    }

    DisposableEffect(buildingId, permissionGranted) {
        if (permissionGranted) {
            viewModel.startScanning()
            onDispose { viewModel.stopScanning() }
        } else {
            onDispose {}
        }
    }

    val transformState = rememberTransformableState { zoomChange, panChange, _ ->
        scale = max(MIN_SCALE, min(MAX_SCALE, scale * zoomChange))
        if (scale > MIN_SCALE) {
            offset = Offset(offset.x + panChange.x, offset.y + panChange.y)
        } else {
            offset = Offset.Zero
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(state.buildingName ?: "Office Map") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState())) {

            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = state.autoFloor,
                    onClick = viewModel::enableAutoFloor,
                    label = { Text("Auto") }
                )
                state.floors.sortedBy { it.level }.forEach { floor ->
                    val label = if (floor.name.isNullOrBlank()) "Floor ${floor.level}" else floor.name
                    FilterChip(
                        selected = state.activeFloorId == floor.id && !state.autoFloor,
                        onClick = { viewModel.selectFloor(floor.id) },
                        label = { Text(label) }
                    )
                }
            }

            Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    when (state.positionSource) {
                        PositionSource.MODEL -> {
                            Text("Source: WiFi Model", style = MaterialTheme.typography.titleSmall)
                            Spacer(Modifier.height(4.dp))
                            val predicted = state.result
                            if (predicted != null) {
                                Text("Cell: ${predicted.predictedCellId ?: "?"}", style = MaterialTheme.typography.bodySmall)
                                Text(
                                    "Center: (${"%.1f".format(predicted.centerX ?: 0.0)}, ${"%.1f".format(predicted.centerY ?: 0.0)})",
                                    style = MaterialTheme.typography.bodySmall
                                )
                                Text(
                                    "Confidence: ${"%.0f".format(predicted.confidence * 100)}%",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = when {
                                        predicted.confidence >= 0.7 -> Color(0xFF16A34A)
                                        predicted.confidence >= 0.4 -> Color(0xFFF59E0B)
                                        else -> Color(0xFFDC2626)
                                    }
                                )
                            } else {
                                Text("Scanning...", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        PositionSource.GPS -> {
                            Text("Source: GPS", style = MaterialTheme.typography.titleSmall)
                            Spacer(Modifier.height(4.dp))
                            val gps = state.gpsPosition
                            if (gps != null) {
                                Text("Lat: ${"%.6f".format(gps.lat)}", style = MaterialTheme.typography.bodySmall)
                                Text("Lng: ${"%.6f".format(gps.lng)}", style = MaterialTheme.typography.bodySmall)
                                Text("Accuracy: ${"%.1f".format(gps.accuracy)} m", style = MaterialTheme.typography.bodySmall)
                                if (gpsOutside) {
                                    Text("GPS fuera del plano conocido", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                                }
                            } else {
                                Text("Waiting for GPS fix...", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                        PositionSource.NONE -> {
                            Text("No positioning source", style = MaterialTheme.typography.titleSmall)
                            Spacer(Modifier.height(4.dp))
                            Text("Scanning for WiFi or GPS...", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    state.error?.let {
                        Spacer(Modifier.height(8.dp))
                        Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            if (!permissionGranted) {
                Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Location permission is required for positioning.", style = MaterialTheme.typography.bodyMedium)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = {
                            permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                        }) { Text("Grant location permission") }
                    }
                }
            }

            val plan = state.floorPlan
            if (plan != null && state.cells.isNotEmpty() && state.gridCellSize > 0f) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(plan.width.toFloat() / plan.height)
                        .padding(horizontal = 16.dp)
                        .clipToBounds()
                ) {
                    Canvas(
                        modifier = Modifier
                            .fillMaxSize()
                            .graphicsLayer {
                                scaleX = scale
                                scaleY = scale
                                translationX = offset.x
                                translationY = offset.y
                            }
                            .transformable(state = transformState)
                    ) {
                        if (planImage != null) {
                            drawImage(
                                image = planImage!!,
                                dstOffset = androidx.compose.ui.unit.IntOffset.Zero,
                                dstSize = androidx.compose.ui.unit.IntSize(size.width.toInt(), size.height.toInt())
                            )
                        }
                        val sx = size.width.toFloat() / plan.width
                        val sy = size.height.toFloat() / plan.height

                        for (cell in state.cells) {
                            val left = cell.column * state.gridCellSize * sx
                            val top = cell.row * state.gridCellSize * sy
                            val w = state.gridCellSize * sx
                            val h = state.gridCellSize * sy
                            val isPredicted = cell.id == state.result?.predictedCellId
                            val color = when {
                                isPredicted -> Color(0xFF16A34A)
                                cell.walkable -> Color(0x3322C55E)
                                else -> Color(0x3390A4AE)
                            }
                            drawRect(color, topLeft = Offset(left, top), size = Size(w, h))
                        }

                        if (state.positionSource == PositionSource.MODEL) {
                            state.result?.let { result ->
                                val cx = result.centerX
                                val cy = result.centerY
                                if (cx != null && cy != null) {
                                    val px = (cx * sx).toFloat()
                                    val py = (cy * sy).toFloat()
                                    drawCircle(color = Color(0xFFDC2626), radius = 10f, center = Offset(px, py))
                                    drawCircle(color = Color(0x66DC2626), radius = 22f, center = Offset(px, py), style = Stroke(width = 3f))
                                }
                            }
                        }

                        if (state.positionSource == PositionSource.GPS) {
                            val pt = gpsPlanPt
                            if (pt != null && !gpsOutside) {
                                val px = pt.x * sx
                                val py = pt.y * sy
                                drawCircle(color = Color(0xFF2563EB), radius = 10f, center = Offset(px, py))
                                drawCircle(color = Color(0x662563EB), radius = 22f, center = Offset(px, py), style = Stroke(width = 3f))
                            }
                        }
                    }

                    FloatingActionButton(
                        onClick = {
                            scale = 1f
                            offset = Offset.Zero
                        },
                        modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp),
                        containerColor = MaterialTheme.colorScheme.surface,
                        contentColor = MaterialTheme.colorScheme.onSurface
                    ) {
                        Icon(Icons.Default.CenterFocusStrong, contentDescription = "Reset zoom")
                    }
                }
            } else {
                Spacer(Modifier.height(8.dp))
                Text(
                    if (state.isLoading) "Loading floor data..." else "No floor data available",
                    modifier = Modifier.padding(horizontal = 16.dp),
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Divider(modifier = Modifier.padding(top = 8.dp))
            Text(
                "Scanned APs (${state.lastScan.size})",
                style = MaterialTheme.typography.titleSmall,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )

            if (state.lastScan.isEmpty()) {
                Text(
                    "No access points detected",
                    modifier = Modifier.padding(horizontal = 16.dp),
                    style = MaterialTheme.typography.bodySmall
                )
            } else {
                LazyColumn(modifier = Modifier.heightIn(max = 240.dp)) {
                    items(state.lastScan.take(20)) { obs ->
                        Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 2.dp)) {
                            Text(obs.bssid, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
                            Text("${obs.rssi} dBm", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}
