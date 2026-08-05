package com.internav.user.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Site
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SiteSelectionUiState(
    val isLoading: Boolean = false,
    val sites: List<Site> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class SiteSelectionViewModel @Inject constructor() : ViewModel() {

    private val _state = MutableStateFlow(SiteSelectionUiState())
    val state: StateFlow<SiteSelectionUiState> = _state

    fun loadSites(orgId: String) {
        _state.value = SiteSelectionUiState(isLoading = true)
        viewModelScope.launch {
            try {
                val response = ApiClient.getService().listSites(orgId)
                if (response.isSuccessful) {
                    val body = response.body()
                    _state.value = SiteSelectionUiState(sites = body?.data ?: emptyList())
                } else {
                    _state.value = SiteSelectionUiState(error = "Failed to load sites")
                }
            } catch (e: Exception) {
                _state.value = SiteSelectionUiState(error = e.message)
            }
        }
    }
}
