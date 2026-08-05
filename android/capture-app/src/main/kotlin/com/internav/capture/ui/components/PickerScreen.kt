package com.internav.capture.ui.components

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.internav.capture.navigation.NavState

data class PickerItem(val id: String, val title: String, val subtitle: String = "")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PickerScreen(
    title: String,
    items: List<PickerItem>,
    loading: Boolean = false,
    error: String? = null,
    onItemSelected: (String) -> Unit,
    onRetry: (() -> Unit)? = null,
    onBack: (() -> Unit)? = null,
    onHome: (() -> Unit)? = null,
    breadcrumbs: List<String> = emptyList()
) {
    BackHandler(enabled = onBack != null) {
        NavState.pop()
        onBack?.invoke()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = {
                            NavState.pop()
                            onBack()
                        }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                        }
                    }
                },
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
                    Text(error, color = MaterialTheme.colorScheme.error)
                    onRetry?.let {
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = it) { Text("Retry") }
                    }
                } else {
                    LazyColumn {
                        items(items) { item ->
                            Card(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable { onItemSelected(item.id) }
                            ) {
                                Column(Modifier.padding(16.dp)) {
                                    Text(item.title, style = MaterialTheme.typography.titleMedium)
                                    if (item.subtitle.isNotBlank()) {
                                        Text(item.subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
