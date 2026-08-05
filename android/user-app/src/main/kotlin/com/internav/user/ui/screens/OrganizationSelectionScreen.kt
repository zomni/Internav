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
import com.internav.user.viewmodel.OrganizationSelectionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrganizationSelectionScreen(
    onOrgSelected: (String) -> Unit,
    viewModel: OrganizationSelectionViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(Unit) { viewModel.loadOrganizations() }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Select Organization") }) }
    ) { padding ->
        when {
            state.isLoading -> CircularProgressIndicator(Modifier.fillMaxSize().wrapContentSize())
            state.error != null -> Text(state.error!!, modifier = Modifier.padding(padding))
            state.organizations.isEmpty() -> {
                Text("No organizations found", modifier = Modifier.fillMaxSize().wrapContentSize().padding(padding))
            }
            else -> {
                LazyColumn(modifier = Modifier.padding(padding).fillMaxSize()) {
                    items(state.organizations) { org ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp)
                                .clickable {
                                    Prefs.saveOrganization(context, org.id)
                                    onOrgSelected(org.id)
                                }
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text(org.name, style = MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }
        }
    }
}
