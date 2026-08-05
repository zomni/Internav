package com.internav.user.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.internav.shared.api.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import dagger.hilt.android.lifecycle.HiltViewModel
import com.internav.shared.model.Organization

data class OrganizationSelectionUiState(
    val isLoading: Boolean = false,
    val organizations: List<Organization> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class OrganizationSelectionViewModel @Inject constructor() : ViewModel() {

    private val _state = MutableStateFlow(OrganizationSelectionUiState())
    val state: StateFlow<OrganizationSelectionUiState> = _state

    fun loadOrganizations() {
        _state.value = OrganizationSelectionUiState(isLoading = true)
        viewModelScope.launch {
            try {
                val response = ApiClient.getService().listOrganizations()
                if (response.isSuccessful) {
                    val body = response.body()
                    _state.value = OrganizationSelectionUiState(
                        organizations = body?.data ?: emptyList()
                    )
                } else {
                    _state.value = OrganizationSelectionUiState(error = "Failed to load organizations")
                }
            } catch (e: Exception) {
                _state.value = OrganizationSelectionUiState(error = e.message)
            }
        }
    }
}
