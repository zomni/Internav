package com.internav.capture.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.internav.shared.local.AppDatabase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReviewScreen(
    onDone: () -> Unit,
    onCaptureMore: () -> Unit,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    var pendingCount by remember { mutableStateOf(0) }
    var completedCount by remember { mutableStateOf(0) }

    LaunchedEffect(Unit) {
        val db = AppDatabase.getInstance(context.applicationContext)
        val dao = db.pendingFingerprintDao()
        pendingCount = withContext(Dispatchers.IO) { dao.getPendingCount() }
        completedCount = withContext(Dispatchers.IO) { dao.getPendingFingerprints().count { it.status == "Completed" } }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Review") },
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
        Column(
            modifier = Modifier.fillMaxSize().padding(paddingValues).padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            if (breadcrumbs.isNotEmpty()) {
                Text(
                    text = breadcrumbs.joinToString("  >  "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp)
                )
            }

            Icon(
                imageVector = Icons.Filled.CheckCircle,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(Modifier.height(16.dp))
            Text("Fingerprint Captured", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(8.dp))
            Text("Saved to offline queue", style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(24.dp))

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Queue Status", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    Text("Pending upload: $pendingCount")
                    Text("Completed: $completedCount")
                }
            }

            Spacer(Modifier.height(24.dp))
            Button(onClick = onCaptureMore, modifier = Modifier.fillMaxWidth()) {
                Text("Capture Another")
            }
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = onDone, modifier = Modifier.fillMaxWidth()) {
                Text("Done")
            }
        }
    }
}
