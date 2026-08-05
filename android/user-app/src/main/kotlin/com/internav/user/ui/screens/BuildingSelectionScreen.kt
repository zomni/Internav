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
import com.internav.user.viewmodel.BuildingSelectionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BuildingSelectionScreen(
    siteId: String,
    onBuildingSelected: (String) -> Unit,
    viewModel: BuildingSelectionViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(siteId) { viewModel.loadBuildings(siteId) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Select Building") },
                navigationIcon = { androidx.compose.material3.TextButton(onClick = {}) { Text("Back") } }
            )
        }
    ) { padding ->
        when {
            state.isLoading -> CircularProgressIndicator(Modifier.fillMaxSize().wrapContentSize())
            state.error != null -> Text(state.error!!, modifier = Modifier.padding(padding))
            state.buildings.isEmpty() -> Text("No buildings found", modifier = Modifier.fillMaxSize().wrapContentSize().padding(padding))
            else -> {
                LazyColumn(modifier = Modifier.padding(padding).fillMaxSize()) {
                    items(state.buildings) { b ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)
                                .clickable {
                                    Prefs.saveBuilding(context, b.id)
                                    onBuildingSelected(b.id)
                                }
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text(b.name, style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
        }
    }
}
