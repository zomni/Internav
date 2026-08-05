package com.internav.user.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.internav.user.viewmodel.FloorSelectionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FloorSelectionScreen(
    buildingId: String,
    onFloorSelected: (String) -> Unit,
    viewModel: FloorSelectionViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(buildingId) { viewModel.loadFloors(buildingId) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Select Floor") },
                navigationIcon = { androidx.compose.material3.TextButton(onClick = {}) { Text("Back") } }
            )
        }
    ) { padding ->
        when {
            state.isLoading -> CircularProgressIndicator(Modifier.fillMaxSize().wrapContentSize())
            state.error != null -> Text(state.error!!, modifier = Modifier.padding(padding))
            state.floors.isEmpty() -> Text("No floors found", modifier = Modifier.fillMaxSize().wrapContentSize().padding(padding))
            else -> {
                LazyColumn(modifier = Modifier.padding(padding).fillMaxSize()) {
                    items(state.floors) { f ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)
                                .clickable { onFloorSelected(f.id) }
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text("Floor ${f.level}", style = MaterialTheme.typography.titleMedium)
                                if (!f.name.isNullOrBlank()) {
                                    Text(f.name, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
