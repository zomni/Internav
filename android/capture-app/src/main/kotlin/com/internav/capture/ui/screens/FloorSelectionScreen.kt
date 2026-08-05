package com.internav.capture.ui.screens

import androidx.compose.runtime.*
import com.internav.capture.ui.components.PickerScreen
import com.internav.capture.ui.components.PickerItem
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Floor
import kotlinx.coroutines.launch

@Composable
fun FloorSelectionScreen(
    buildingId: String,
    onFloorSelected: (String, String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<Floor>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    val load: suspend () -> Unit = {
        loading = true; error = null
        try {
            val resp = ApiClient.getService().listFloors()
            if (resp.isSuccessful) items = resp.body()?.data?.filter { it.buildingId == buildingId } ?: emptyList()
            else error = "Failed to load floors"
        } catch (e: Exception) { error = e.message }
        finally { loading = false }
    }

    LaunchedEffect(buildingId) { load() }

    PickerScreen(
        title = "Select Floor",
        items = items.map { PickerItem(it.id, it.name, "Level ${it.level}") },
        loading = loading, error = error,
        onItemSelected = { floorId ->
            val name = items.find { it.id == floorId }?.name ?: ""
            onFloorSelected(floorId, name)
        },
        onRetry = { scope.launch { load() } },
        onBack = onBack,
        onHome = onHome,
        breadcrumbs = breadcrumbs
    )
}
