package com.internav.capture.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.internav.capture.ui.components.PickerScreen
import com.internav.capture.ui.components.PickerItem
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Campaign
import kotlinx.coroutines.launch

@Composable
fun CampaignSelectionScreen(
    floorId: String,
    onCampaignSelected: (String, String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<Campaign>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    val load: suspend () -> Unit = {
        loading = true; error = null
        try {
            val resp = ApiClient.getService().listCampaigns(floorId)
            if (resp.isSuccessful) {
                items = resp.body()?.data?.filter { !it.isDeleted && (it.status == "Collecting" || it.status == "Paused") } ?: emptyList()
            } else error = "Failed to load campaigns"
        } catch (e: Exception) { error = e.message }
        finally { loading = false }
    }

    LaunchedEffect(floorId) { load() }

    if (!loading && items.isEmpty() && error == null) {
        Column(Modifier.fillMaxSize().padding(16.dp)) {
            Text("Select Campaign", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(16.dp))
            Text("No campaigns available for capture. A campaign must be in Collecting or Paused state.")
            Spacer(Modifier.height(8.dp))
            Button(onClick = { scope.launch { load() } }) { Text("Refresh") }
        }
    } else {
        PickerScreen(
            title = "Select Campaign",
            items = items.map { PickerItem(it.id, it.name, it.status) },
            loading = loading, error = error,
            onItemSelected = { campaignId ->
                val name = items.find { it.id == campaignId }?.name ?: ""
                onCampaignSelected(campaignId, name)
            },
            onRetry = { scope.launch { load() } },
            onBack = onBack,
            onHome = onHome,
            breadcrumbs = breadcrumbs
        )
    }
}
