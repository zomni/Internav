package com.internav.capture.ui.screens

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
import com.internav.shared.local.AppDatabase
import com.internav.shared.local.PendingFingerprintEntity
import com.internav.shared.sync.SyncWorker
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
    var syncing by remember { mutableStateOf(false) }
    var syncResult by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun load() {
        scope.launch {
            val db = AppDatabase.getInstance(context.applicationContext)
            val dao = db.pendingFingerprintDao()
            val all = withContext(Dispatchers.IO) {
                dao.getPendingFingerprints() + dao.getUploadingFingerprints() + dao.getFailedFingerprintsReadyForRetry(System.currentTimeMillis())
            }
            fingerprints = all.distinctBy { it.id }
        }
    }

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
                                SyncWorker.enqueue(context)
                                syncResult = "Sync scheduled"
                                load()
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
            Text("${fingerprints.size} items", style = MaterialTheme.typography.titleSmall)

            LazyColumn(modifier = Modifier.weight(1f)) {
                items(fingerprints) { fp ->
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
                                    "Failed" -> MaterialTheme.colorScheme.error
                                    else -> MaterialTheme.colorScheme.onSurfaceVariant
                                }
                            )
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text("Cell: ${fp.cellId.take(8)}...", style = MaterialTheme.typography.bodyMedium)
                                Text("Status: ${fp.status} | Retries: ${fp.retryCount}", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}
