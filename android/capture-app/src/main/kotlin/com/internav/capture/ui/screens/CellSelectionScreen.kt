package com.internav.capture.ui.screens

import android.graphics.BitmapFactory
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.internav.capture.navigation.NavState
import com.internav.capture.ui.components.CellMap
import com.internav.capture.ui.utils.cellCaptureColor
import com.internav.capture.ui.utils.cellLabel
import com.internav.shared.api.ApiClient
import com.internav.shared.graphics.decodeFloorPlanImage
import com.internav.shared.model.Cell
import com.internav.shared.model.FloorPlan
import com.internav.shared.model.Grid
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CellSelectionScreen(
    campaignId: String,
    floorId: String,
    onCellSelected: (String, String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    var allCells by remember { mutableStateOf<List<Cell>>(emptyList()) }
    var grid by remember { mutableStateOf<Grid?>(null) }
    var plan by remember { mutableStateOf<FloorPlan?>(null) }
    var planImage by remember { mutableStateOf<ImageBitmap?>(null) }
    var showMap by remember { mutableStateOf(true) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var captureCounts by remember { mutableStateOf<Map<String, Int>>(emptyMap()) }
    val scope = rememberCoroutineScope()

    val walkableCells = allCells.filter { it.walkable }

    LaunchedEffect(floorId) {
        try {
            val gridResp = ApiClient.getService().listGrids(floorId)
            if (gridResp.isSuccessful) {
                val grids = gridResp.body()?.data ?: emptyList()
                val activeGrid = grids.firstOrNull { it.status == "Active" }
                if (activeGrid != null) {
                    grid = activeGrid
                    val cellResp = ApiClient.getService().listCells(activeGrid.id)
                    if (cellResp.isSuccessful) {
                        allCells = cellResp.body()?.data ?: emptyList()
                    } else error = "Failed to load cells"
                } else error = "No active grid for this floor"

                val fpResp = ApiClient.getService().listFingerprints(campaignId)
                if (fpResp.isSuccessful) {
                    val fps = fpResp.body()?.data ?: emptyList()
                    captureCounts = fps.groupBy { it.cellId }.mapValues { it.value.size }
                }

                val planResp = ApiClient.getService().listFloorPlans(floorId)
                val activePlan = planResp.body()?.data?.firstOrNull { it.isActive }
                if (activePlan != null) {
                    plan = activePlan
                    val imgResp = withContext(Dispatchers.IO) {
                        ApiClient.getService().downloadFloorPlanImage(activePlan.id)
                    }
                    if (imgResp.isSuccessful) {
                        val bmp = withContext(Dispatchers.IO) {
                            imgResp.body()?.bytes()?.let { decodeFloorPlanImage(it) }
                        }
                        if (bmp != null) planImage = bmp.asImageBitmap()
                        else error = "Failed to decode floor plan"
                    } else error = "Failed to download floor plan"
                }
            } else error = "Failed to load grid"
        } catch (e: Exception) { error = e.message }
        finally { loading = false }
    }

    BackHandler(enabled = onBack != null) {
        NavState.pop()
        onBack?.invoke()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Select Cell") },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    }
                },
                actions = {
                    if (onHome != null) {
                        IconButton(onClick = onHome) {
                            Icon(Icons.Default.Home, contentDescription = "Home")
                        }
                    }
                }
            )
        }
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (breadcrumbs.isNotEmpty()) {
                Text(
                    text = breadcrumbs.joinToString("  >  "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                if (loading) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                } else if (error != null) {
                    Text(error!!, color = MaterialTheme.colorScheme.error)
                } else {
                    Text("${walkableCells.size} walkable cells available", style = MaterialTheme.typography.bodySmall)
                    Spacer(Modifier.height(8.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = showMap, onClick = { showMap = true }, label = { Text("Map") })
                        FilterChip(selected = !showMap, onClick = { showMap = false }, label = { Text("List") })
                    }
                    Spacer(Modifier.height(8.dp))

                    if (showMap) {
                        if (plan != null && planImage != null && grid != null) {
                            CellMap(
                                plan = plan!!,
                                planImage = planImage,
                                gridCellSize = grid!!.cellSize.toFloat(),
                                cells = allCells,
                                captureCounts = captureCounts,
                                onCellTap = { cell ->
                                    if (cell.walkable) onCellSelected(cell.id, cellLabel(cell, allCells))
                                },
                                modifier = Modifier.fillMaxWidth()
                            )
                        } else {
                            Text("Floor plan unavailable", style = MaterialTheme.typography.bodySmall)
                        }
                    } else {
                        LazyVerticalGrid(
                            columns = GridCells.Adaptive(minSize = 80.dp),
                            contentPadding = PaddingValues(4.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            items(walkableCells) { cell ->
                                Card(
                                    modifier = Modifier.aspectRatio(1f),
                                    onClick = { onCellSelected(cell.id, cellLabel(cell, allCells)) }
                                ) {
                                    Column(Modifier.fillMaxSize().padding(4.dp), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(
                                            cellLabel(cell, allCells),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = cellCaptureColor(captureCounts[cell.id] ?: 0),
                                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                        )
                                        Text(
                                            "${captureCounts[cell.id] ?: 0} capturas",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
