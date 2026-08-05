package com.internav.user.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.internav.shared.api.ApiClient
import com.internav.shared.model.Floor
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FloorSelectionUiState(
    val isLoading: Boolean = false,
    val floors: List<Floor> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class FloorSelectionViewModel @Inject constructor() : ViewModel() {

    private val _state = MutableStateFlow(FloorSelectionUiState())
    val state: StateFlow<FloorSelectionUiState> = _state

    fun loadFloors(buildingId: String) {
        _state.value = FloorSelectionUiState(isLoading = true)
        viewModelScope.launch {
            try {
                val response = ApiClient.getService().listFloors(buildingId)
                if (response.isSuccessful) {
                    val body = response.body()
                    _state.value = FloorSelectionUiState(floors = body?.data ?: emptyList())
                } else {
                    _state.value = FloorSelectionUiState(error = "Failed to load floors")
                }
            } catch (e: Exception) {
                _state.value = FloorSelectionUiState(error = e.message)
            }
        }
    }
}
