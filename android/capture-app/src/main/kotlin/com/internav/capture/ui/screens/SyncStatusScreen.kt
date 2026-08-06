package com.internav.capture.ui.screens

import android.util.Log
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.internav.capture.ui.utils.cellLabel
import com.internav.shared.api.ApiClient
import com.internav.shared.local.AppDatabase
import com.internav.shared.local.PendingFingerprintEntity
import com.internav.shared.sync.SyncManager
import com.internav.shared.sync.SyncResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncStatusScreen(
    onBackToOrganizations: () -> Unit,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var fingerprints by remember { mutableStateOf<List<PendingFingerprintEntity>>(emptyList()) }
    var serverCounts by remember { mutableStateOf<Map<String, Int>>(emptyMap()) }
    var syncing by remember { mutableStateOf(false) }
    var syncResult by remember { mutableStateOf<String?>(null) }
    var backfillDone by remember { mutableStateOf(false) }
    var lastServerFetch by remember { mutableStateOf(0L) }
    val scope = rememberCoroutineScope()

    suspend fun backfillLabels(dao: com.internav.shared.local.PendingFingerprintDao, fps: List<PendingFingerprintEntity>) {
        if (backfillDone) return
        backfillDone = true
        val missing = fps.filter { it.cellLabel == null }
        val campaigns = missing.map { it.campaignId }.distinct()
        if (campaigns.isEmpty()) return
        withContext(Dispatchers.IO) {
            for (cid in campaigns) {
                try {
                    val campResp = ApiClient.getService().getCampaign(cid)
                    val floorId = campResp.body()?.data?.floorId ?: continue
                    val gridResp = ApiClient.getService().listGrids(floorId)
                    val grid = gridResp.body()?.data?.firstOrNull { it.status == "Active" } ?: continue
                    val cellResp = ApiClient.getService().listCells(grid.id)
                    val cells = cellResp.body()?.data ?: continue
                    if (cells.isEmpty()) continue
                    val labels = cells.associate { it.id to cellLabel(it, cells) }
                    missing.filter { it.campaignId == cid }
                        .map { it.cellId }
                        .distinct()
                        .forEach { cellId -> labels[cellId]?.let { dao.updateCellLabel(cellId, it) } }
                } catch (e: Exception) {
                    Log.e("SyncStatusScreen", "Label backfill failed for campaign $cid", e)
                }
            }
        }
    }

    suspend fun fetchServerCounts(fps: List<PendingFingerprintEntity>) {
        val campaigns = fps.map { it.campaignId }.distinct()
        if (campaigns.isEmpty()) {
            serverCounts = emptyMap()
            return
        }
        val counts = mutableMapOf<String, Int>()
        withContext(Dispatchers.IO) {
            for (cid in campaigns) {
                try {
                    val resp = ApiClient.getService().listFingerprints(cid)
                    if (resp.isSuccessful) {
                        val data = resp.body()?.data ?: emptyList()
                        data.forEach { counts[it.cellId] = (counts[it.cellId] ?: 0) + 1 }
                    }
                } catch (e: Exception) {
                    Log.e("SyncStatusScreen", "Fetch server counts failed for campaign $cid", e)
                }
            }
        }
        serverCounts = counts
    }

    fun load(forceServer: Boolean = false) {
        scope.launch {
            val db = AppDatabase.getInstance(context.applicationContext)
            val dao = db.pendingFingerprintDao()
            var fps = withContext(Dispatchers.IO) { dao.getAllFingerprints() }
            if (fps.any { it.cellLabel == null }) {
                backfillLabels(dao, fps)
                fps = withContext(Dispatchers.IO) { dao.getAllFingerprints() }
            }
            fingerprints = fps
            val now = System.currentTimeMillis()
            if (forceServer || now - lastServerFetch >= 5000) {
                lastServerFetch = now
                fetchServerCounts(fps)
            }
        }
    }

    val grouped = fingerprints.groupBy { it.cellId }

    LaunchedEffect(Unit) {
        load()
        while (true) {
            kotlinx.coroutines.delay(2000)
            load()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sync Status") },
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
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues).padding(16.dp)) {
            if (breadcrumbs.isNotEmpty()) {
                Text(
                    text = breadcrumbs.joinToString("  >  "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 4.dp)
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = {
                        scope.launch {
                            syncing = true
                            syncResult = null
                            try {
                                val db = AppDatabase.getInstance(context.applicationContext)
                                val dao = db.pendingFingerprintDao()
                                val result = withContext(Dispatchers.IO) {
                                    ApiClient.ensureReady(context.applicationContext)
                                    SyncManager(dao).syncPending()
                                }
                                syncResult = when (result) {
                                    is SyncResult.NoOp -> "No pending fingerprints to sync"
                                    is SyncResult.Completed -> {
                                        val summary = "Sync complete: ${result.successCount} uploaded, " +
                                            "${result.rejectedCount} rejected, ${result.failCount} failed"
                                        if (result.errors.isEmpty()) summary
                                        else summary + "\n" + result.errors.take(8).joinToString("\n")
                                    }
                                }
                                load(forceServer = true)
                            } catch (e: Exception) {
                                syncResult = "Error: ${e.message}"
                            } finally {
                                syncing = false
                            }
                        }
                    },
                    enabled = !syncing,
                    modifier = Modifier.weight(1f)
                ) {
                    if (syncing) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else {
                        Icon(Icons.Default.Sync, contentDescription = null)
                        Spacer(Modifier.width(4.dp))
                        Text("Sync Now")
                    }
                }
                OutlinedButton(onClick = onBackToOrganizations, modifier = Modifier.weight(1f)) {
                    Text("Back to Menu")
                }
            }

            if (syncResult != null) {
                Spacer(Modifier.height(8.dp))
                Text(syncResult!!, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(12.dp))
            Text(
                "${fingerprints.size} captures | ${grouped.size} cells",
                style = MaterialTheme.typography.titleSmall
            )

            if (fingerprints.isEmpty()) {
                Spacer(Modifier.height(24.dp))
                Text(
                    "No fingerprints stored locally yet",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            LazyColumn(modifier = Modifier.weight(1f)) {
                grouped.forEach { (cellId, items) ->
                    item(key = "cell-$cellId") {
                        val label = items.firstNotNullOfOrNull { it.cellLabel } ?: cellId
                        val serverCount = serverCounts[cellId] ?: 0
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
                        ) {
                            Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text("Cell: $label", style = MaterialTheme.typography.titleSmall)
                                    Text("${items.size} local", style = MaterialTheme.typography.bodySmall)
                                    Text("Backend: $serverCount", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                    items(items, key = { it.id }) { fp ->
                        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
                            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = when (fp.status) {
                                        "Pending" -> Icons.Default.HourglassEmpty
                                        "Uploading" -> Icons.Default.Sync
                                        "Completed" -> Icons.Default.CheckCircle
                                        else -> Icons.Default.Error
                                    },
                                    contentDescription = null,
                                    tint = when (fp.status) {
                                        "Completed" -> MaterialTheme.colorScheme.primary
                                        "Failed", "Rejected" -> MaterialTheme.colorScheme.error
                                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                                    }
                                )
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("Sample #${fp.sampleNumber} — ${fp.cellLabel ?: fp.cellId}", style = MaterialTheme.typography.bodyMedium)
                                    Text("Status: ${fp.status} | Retries: ${fp.retryCount}", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
