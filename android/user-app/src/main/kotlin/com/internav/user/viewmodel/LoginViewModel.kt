package com.internav.user.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.internav.shared.api.ApiClient
import com.internav.shared.model.LoginRequest
import com.google.gson.JsonParser
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val serverUrl: String = "https://gear-glowing-unwary.ngrok-free.dev",
    val email: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class LoginViewModel @Inject constructor(
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state

    init {
        val savedUrl = context.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
            .getString("server_url", null)
        if (savedUrl != null) {
            _state.value = _state.value.copy(serverUrl = savedUrl)
        }
    }

    fun onServerUrlChanged(url: String) { _state.value = _state.value.copy(serverUrl = url, error = null) }
    fun onEmailChanged(email: String) { _state.value = _state.value.copy(email = email, error = null) }
    fun onPasswordChanged(password: String) { _state.value = _state.value.copy(password = password, error = null) }

    fun isLoggedIn() = ApiClient.tokenManager.getValidToken() != null

    fun login(onSuccess: () -> Unit) {
        val s = _state.value
        if (s.email.isBlank() || s.password.isBlank() || s.serverUrl.isBlank()) return
        val email = s.email.trim().lowercase()
        _state.value = s.copy(isLoading = true, error = null)

        viewModelScope.launch {
            try {
                ApiClient.initialize(s.serverUrl, context)
                val prefs = context.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
                prefs.edit().putString("server_url", s.serverUrl).apply()
                val response = ApiClient.getPublicService().login(LoginRequest(email = email, password = s.password))
                if (response.isSuccessful) {
                    val body = response.body()
                    val data = body?.data
                    if (body?.success == true && data != null) {
                        ApiClient.tokenManager.updateTokens(data.accessToken, data.refreshToken)
                        _state.value = _state.value.copy(isLoading = false)
                        onSuccess()
                    } else {
                        _state.value = _state.value.copy(isLoading = false, error = body?.message ?: "Login failed")
                    }
                } else {
                    val detail = response.errorBody()?.string()?.let { raw ->
                        runCatching {
                            JsonParser.parseString(raw).asJsonObject.get("detail")?.asString
                        }.getOrNull()
                    }
                    val base = if (detail != null) {
                        "Login failed (${response.code()}) - $detail"
                    } else {
                        "Login failed (${response.code()}) - URL: ${s.serverUrl}"
                    }
                    _state.value = _state.value.copy(
                        isLoading = false,
                        error = "$base (email='$email', len=${email.length})"
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Login failed")
            }
        }
    }
}
