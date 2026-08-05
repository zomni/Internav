package com.internav.user.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Building
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BuildingSelectionUiState(
    val isLoading: Boolean = false,
    val buildings: List<Building> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class BuildingSelectionViewModel @Inject constructor() : ViewModel() {

    private val _state = MutableStateFlow(BuildingSelectionUiState())
    val state: StateFlow<BuildingSelectionUiState> = _state

    fun loadBuildings(siteId: String) {
        _state.value = BuildingSelectionUiState(isLoading = true)
        viewModelScope.launch {
            try {
                val response = ApiClient.getService().listBuildings(siteId)
                if (response.isSuccessful) {
                    val body = response.body()
                    _state.value = BuildingSelectionUiState(buildings = body?.data ?: emptyList())
                } else {
                    _state.value = BuildingSelectionUiState(error = "Failed to load buildings")
                }
            } catch (e: Exception) {
                _state.value = BuildingSelectionUiState(error = e.message)
            }
        }
    }
}
