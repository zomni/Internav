package com.internav.user.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.internav.user.util.Prefs
import com.internav.user.viewmodel.SiteSelectionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SiteSelectionScreen(
    organizationId: String,
    onSiteSelected: (String) -> Unit,
    viewModel: SiteSelectionViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(organizationId) { viewModel.loadSites(organizationId) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Select Site") },
                navigationIcon = { androidx.compose.material3.TextButton(onClick = {}) { Text("Back") } }
            )
        }
    ) { padding ->
        when {
            state.isLoading -> CircularProgressIndicator(Modifier.fillMaxSize().wrapContentSize())
            state.error != null -> Text(state.error!!, modifier = Modifier.padding(padding))
            state.sites.isEmpty() -> Text("No sites found", modifier = Modifier.fillMaxSize().wrapContentSize().padding(padding))
            else -> {
                LazyColumn(modifier = Modifier.padding(padding).fillMaxSize()) {
                    items(state.sites) { site ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)
                                .clickable {
                                    Prefs.saveSite(context, site.id)
                                    onSiteSelected(site.id)
                                }
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text(site.name, style = MaterialTheme.typography.titleMedium)
                                val address = site.address
                                if (!address.isNullOrBlank()) {
                                    Text(address, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
