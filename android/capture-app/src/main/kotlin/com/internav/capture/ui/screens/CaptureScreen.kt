package com.internav.capture.ui.screens

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.SystemClock
import android.provider.Settings
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.internav.capture.navigation.NavState
import com.internav.capture.ui.components.CellMap
import com.internav.capture.ui.utils.WifiScanThrottle
import com.internav.shared.api.ApiClient
import com.internav.shared.graphics.decodeFloorPlanImage
import com.internav.shared.local.AppDatabase
import com.internav.shared.model.Cell
import com.internav.shared.model.FloorPlan
import com.internav.shared.model.ObservationRequest
import com.internav.shared.sync.SyncManager
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant

data class ScanResult(
    val bssid: String,
    val ssid: String,
    val rssi: Int,
    val frequency: Int
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaptureScreen(
    campaignId: String,
    floorId: String,
    cellId: String,
    cellLabel: String,
    onFingerprintCaptured: (String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var scanResults by remember { mutableStateOf<List<ScanResult>>(emptyList()) }
    var scanning by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var permissionDenied by remember { mutableStateOf(false) }
    var savedId by remember { mutableStateOf<String?>(null) }
    var sampleNumber by remember { mutableStateOf(1) }
    var floorPlan by remember { mutableStateOf<FloorPlan?>(null) }
    var planImage by remember { mutableStateOf<ImageBitmap?>(null) }
    var gridCellSize by remember { mutableStateOf(0f) }
    var cells by remember { mutableStateOf<List<Cell>>(emptyList()) }
    var retryCountdown by remember { mutableStateOf(0) }
    var backendCount by remember { mutableStateOf<Int?>(null) }

    LaunchedEffect(campaignId, cellId) {
        try {
            val resp = withContext(Dispatchers.IO) {
                ApiClient.getService().listFingerprints(campaignId)
            }
            if (resp.isSuccessful) {
                val data = resp.body()?.data ?: emptyList()
                backendCount = data.count { it.cellId == cellId }
            }
        } catch (e: Exception) {
            backendCount = null
        }
    }

    LaunchedEffect(floorId) {
        WifiScanThrottle.attach(context.applicationContext)
        try {
            val gridResp = ApiClient.getService().listGrids(floorId)
            val activeGrid = gridResp.body()?.data?.firstOrNull { it.status == "Active" }
            if (gridResp.isSuccessful && activeGrid != null) {
                gridCellSize = activeGrid.cellSize.toFloat()
                val cellResp = ApiClient.getService().listCells(activeGrid.id)
                if (cellResp.isSuccessful) cells = cellResp.body()?.data ?: emptyList()
            }
            val planResp = ApiClient.getService().listFloorPlans(floorId)
            val activePlan = planResp.body()?.data?.firstOrNull { it.isActive }
            if (activePlan != null) {
                floorPlan = activePlan
                val imgResp = withContext(Dispatchers.IO) {
                    ApiClient.getService().downloadFloorPlanImage(activePlan.id)
                }
                if (imgResp.isSuccessful) {
                    val bmp = withContext(Dispatchers.IO) {
                        imgResp.body()?.bytes()?.let { decodeFloorPlanImage(it) }
                    }
                    if (bmp != null) planImage = bmp.asImageBitmap()
                }
            }
        } catch (e: Exception) {
            // Map is optional; capture flow continues without it.
        }
    }

    LaunchedEffect(cellId) {
        val db = AppDatabase.getInstance(context.applicationContext)
        val maxSample = withContext(Dispatchers.IO) {
            db.pendingFingerprintDao().getMaxSampleNumberForCell(cellId)
        }
        sampleNumber = maxSample + 1
    }

    suspend fun performScan() {
        scanning = true
        error = null
        retryCountdown = 0
        try {
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            if (!wifiManager.isWifiEnabled) {
                error = "WiFi is disabled. Please enable WiFi."
                return
            }

            while (true) {
                val now = SystemClock.elapsedRealtime()
                val scanStarted = withContext(Dispatchers.IO) { wifiManager.startScan() }
                if (scanStarted) {
                    WifiScanThrottle.recordScan(now)
                    break
                }

                val waitMs = WifiScanThrottle.waitMsUntilAllowed(now)
                if (waitMs <= 0L) {
                    error = "Failed to start WiFi scan"
                    return
                }

                val deadline = now + waitMs
                while (SystemClock.elapsedRealtime() < deadline) {
                    val remaining = deadline - SystemClock.elapsedRealtime()
                    retryCountdown = ((remaining + 999L) / 1000L).toInt()
                    kotlinx.coroutines.delay(1000)
                }
                retryCountdown = 0
            }

            kotlinx.coroutines.delay(2000)

            val results = withContext(Dispatchers.IO) {
                wifiManager.scanResults?.mapNotNull { sr ->
                    if (sr.BSSID.isNotBlank() && sr.level in -100..0 && sr.frequency > 0) {
                        ScanResult(sr.BSSID, sr.SSID, sr.level, sr.frequency)
                    } else null
                } ?: emptyList()
            }
            scanResults = results.sortedByDescending { it.rssi }
        } catch (e: Exception) {
            error = e.message ?: "Scan failed"
        } finally {
            scanning = false
            retryCountdown = 0
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        permissionDenied = !granted
        if (granted) scope.launch { performScan() }
        else error = "Location permission denied. WiFi scanning requires location access."
    }

    fun requestScan() {
        val hasPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (hasPermission) {
            scope.launch { performScan() }
        } else {
            permissionDenied = false
            error = null
            permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    suspend fun saveFingerprint() {
        if (scanResults.isEmpty()) {
            error = "No scan results to save"
            return
        }
        saving = true
        error = null
        try {
            val observations = scanResults.map {
                ObservationRequest(bssid = it.bssid, ssid = it.ssid, rssi = it.rssi, frequency = it.frequency)
            }
            val db = AppDatabase.getInstance(context.applicationContext)
            val syncManager = SyncManager(db.pendingFingerprintDao())
            val id = withContext(Dispatchers.IO) {
                syncManager.enqueueFingerprint(
                    campaignId = campaignId,
                    cellId = cellId,
                    cellLabel = cellLabel,
                    deviceId = android.os.Build.MODEL + "-" + android.os.Build.ID,
                    capturedAt = Instant.now().toString(),
                    sampleNumber = sampleNumber,
                    orientation = 0.0,
                    notes = null,
                    observations = observations
                )
            }
            savedId = id.toString()
            sampleNumber++
            scanResults = emptyList()
        } catch (e: Exception) {
            error = e.message ?: "Save failed"
        } finally {
            saving = false
        }
    }

    BackHandler(enabled = onBack != null) {
        NavState.pop()
        onBack?.invoke()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Capture Fingerprint") },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = {
                            NavState.pop()
                            onBack()
                        }) {
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
                val backendText = backendCount?.let { " | Backend: $it" } ?: ""
                Text(
                    "Cell: $cellLabel | Sample: $sampleNumber$backendText",
                    style = MaterialTheme.typography.bodySmall
                )
                Spacer(Modifier.height(8.dp))

                if (floorPlan != null && planImage != null && gridCellSize > 0f) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                            .clipToBounds(),
                        contentAlignment = Alignment.Center
                    ) {
                        CellMap(
                            plan = floorPlan!!,
                            planImage = planImage,
                            gridCellSize = gridCellSize,
                            cells = cells,
                            selectedCellId = cellId,
                            focusedCellId = cellId,
                            modifier = Modifier.fillMaxWidth()
                        )
                        Surface(
                            color = MaterialTheme.colorScheme.surface.copy(alpha = 0.88f),
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(4.dp)
                        ) {
                            Text(
                                "Cell: $cellLabel | Sample: $sampleNumber$backendText",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }

                if (error != null) {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer), modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp)) {
                            Text(error!!, color = MaterialTheme.colorScheme.onErrorContainer)
                            if (permissionDenied) {
                                Spacer(Modifier.height(8.dp))
                                OutlinedButton(onClick = {
                                    val intent = Intent(
                                        Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                        Uri.fromParts("package", context.packageName, null)
                                    )
                                    context.startActivity(intent)
                                }) {
                                    Text("Open Settings")
                                }
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }

                if (retryCountdown > 0) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            "Android scan limit reached. Retrying automatically in ${retryCountdown}s...",
                            color = MaterialTheme.colorScheme.onTertiaryContainer,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(onClick = { requestScan() }, enabled = !scanning && !saving, modifier = Modifier.weight(1f)) {
                        if (scanning) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                        else Text("Scan WiFi")
                    }
                    Button(
                        onClick = { scope.launch { saveFingerprint() } },
                        enabled = scanResults.isNotEmpty() && !saving,
                        modifier = Modifier.weight(1f)
                    ) {
                        if (saving) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                        else Text("Save Offline")
                    }
                }

                if (savedId != null) {
                    Spacer(Modifier.height(8.dp))
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                        Column(Modifier.padding(12.dp)) {
                            Text("Saved to queue (#$savedId)", style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.height(4.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(onClick = { savedId = null; onFingerprintCaptured(savedId ?: "") }, modifier = Modifier.weight(1f)) {
                                    Text("Review")
                                }
                            }
                        }
                    }
                }

                Spacer(Modifier.height(12.dp))
                Text("${scanResults.size} APs detected", style = MaterialTheme.typography.titleSmall)

                LazyColumn(modifier = Modifier.weight(1f)) {
                    val grouped = scanResults.groupBy { if (it.ssid.isBlank()) "(hidden)" else it.ssid }
                    grouped.entries.forEach { (ssid, aps) ->
                        item {
                            Text(
                                text = "$ssid  (${aps.size} APs)",
                                style = MaterialTheme.typography.titleSmall,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(start = 4.dp, top = 8.dp, bottom = 4.dp)
                            )
                        }
                        items(aps) { ap ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(start = 12.dp, top = 1.dp, bottom = 1.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                                )
                            ) {
                                Row(Modifier.padding(horizontal = 8.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text(ap.bssid, style = MaterialTheme.typography.bodySmall, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
                                    }
                                    Text("${ap.rssi} dBm", style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
