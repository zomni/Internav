package com.internav.capture.ui.screens

import androidx.compose.runtime.*
import com.internav.capture.ui.components.PickerScreen
import com.internav.capture.ui.components.PickerItem
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Building
import kotlinx.coroutines.launch

@Composable
fun BuildingSelectionScreen(
    siteId: String,
    onBuildingSelected: (String, String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<Building>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    val load: suspend () -> Unit = {
        loading = true; error = null
        try {
            val resp = ApiClient.getService().listBuildings()
            if (resp.isSuccessful) items = resp.body()?.data?.filter { it.siteId == siteId } ?: emptyList()
            else error = "Failed to load buildings"
        } catch (e: Exception) { error = e.message }
        finally { loading = false }
    }

    LaunchedEffect(siteId) { load() }

    PickerScreen(
        title = "Select Building",
        items = items.map { PickerItem(it.id, it.name, it.code) },
        loading = loading, error = error,
        onItemSelected = { buildingId ->
            val name = items.find { it.id == buildingId }?.name ?: ""
            onBuildingSelected(buildingId, name)
        },
        onRetry = { scope.launch { load() } },
        onBack = onBack,
        onHome = onHome,
        breadcrumbs = breadcrumbs
    )
}
