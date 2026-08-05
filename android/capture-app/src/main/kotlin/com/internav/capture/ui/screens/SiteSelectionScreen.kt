package com.internav.capture.ui.screens

import androidx.compose.runtime.*
import com.internav.capture.ui.components.PickerScreen
import com.internav.capture.ui.components.PickerItem
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Site
import kotlinx.coroutines.launch

@Composable
fun SiteSelectionScreen(
    organizationId: String,
    onSiteSelected: (String, String) -> Unit,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<Site>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    val load: suspend () -> Unit = {
        loading = true; error = null
        try {
            val resp = ApiClient.getService().listSites()
            if (resp.isSuccessful) items = resp.body()?.data?.filter { it.organizationId == organizationId } ?: emptyList()
            else error = "Failed to load sites"
        } catch (e: Exception) { error = e.message }
        finally { loading = false }
    }

    LaunchedEffect(organizationId) { load() }

    PickerScreen(
        title = "Select Site",
        items = items.map { PickerItem(it.id, it.name, it.code) },
        loading = loading, error = error,
        onItemSelected = { siteId ->
            val name = items.find { it.id == siteId }?.name ?: ""
            onSiteSelected(siteId, name)
        },
        onRetry = { scope.launch { load() } },
        onBack = onBack,
        onHome = onHome,
        breadcrumbs = breadcrumbs
    )
}
