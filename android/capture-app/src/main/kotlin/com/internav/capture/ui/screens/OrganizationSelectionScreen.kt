package com.internav.capture.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Organization
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrganizationSelectionScreen(
    onOrgSelected: (String, String) -> Unit,
    onSyncStatus: () -> Unit,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    var orgs by remember { mutableStateOf<List<Organization>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        try {
            val response = ApiClient.getService().listOrganizations()
            if (response.isSuccessful) orgs = response.body()?.data ?: emptyList()
            else error = "Failed to load organizations"
        } catch (e: Exception) {
            error = e.message
        } finally {
            loading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Select Organization") },
                actions = {
                    IconButton(onClick = onSyncStatus) {
                        Icon(Icons.Default.Sync, contentDescription = "Sync Status")
                    }
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
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else if (error != null) {
                    Text(error!!, color = MaterialTheme.colorScheme.error)
                } else {
                    LazyColumn {
                        items(orgs) { org ->
                            Card(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable { onOrgSelected(org.id, org.name) }
                            ) {
                                Column(Modifier.padding(16.dp)) {
                                    Text(org.name, style = MaterialTheme.typography.titleMedium)
                                    Text(org.code, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
