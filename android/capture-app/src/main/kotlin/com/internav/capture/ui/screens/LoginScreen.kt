package com.internav.capture.ui.screens

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.internav.shared.api.ApiClient
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var serverUrl by remember { mutableStateOf("http://10.0.2.2:8000") }
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        val prefs = context.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
        prefs.getString("server_url", null)?.let { serverUrl = it }
    }
    val scope = rememberCoroutineScope()

    MaterialTheme {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text("IPP Capture", style = MaterialTheme.typography.headlineMedium)
                Spacer(Modifier.height(8.dp))
                Text("Indoor Positioning Platform", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(32.dp))

                OutlinedTextField(
                    value = serverUrl,
                    onValueChange = { serverUrl = it },
                    label = { Text("Server URL") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(12.dp))

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Password") },
                    singleLine = true,
                    visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(16.dp))

                if (error != null) {
                    Text(error!!, color = MaterialTheme.colorScheme.error)
                    Spacer(Modifier.height(8.dp))
                }

                Button(
                    onClick = {
                        scope.launch {
                            loading = true
                            error = null
                            try {
                                ApiClient.initialize(serverUrl, context)
                                val prefs = context.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
                                prefs.edit().putString("server_url", serverUrl).apply()
                                val response = ApiClient.getPublicService().login(
                                    com.internav.shared.model.LoginRequest(email, password)
                                )
                                if (response.isSuccessful && response.body()?.success == true) {
                                    val data = response.body()!!.data!!
                                    ApiClient.tokenManager.updateTokens(data.accessToken, data.refreshToken)
                                    onLoginSuccess()
                                } else {
                                    error = "Login failed: check credentials"
                                }
                            } catch (e: Exception) {
                                error = e.message ?: "Connection failed"
                            } finally {
                                loading = false
                            }
                        }
                    },
                    enabled = !loading && email.isNotBlank() && password.isNotBlank() && serverUrl.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (loading) CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    else Text("Sign In")
                }
            }
        }
    }
}
