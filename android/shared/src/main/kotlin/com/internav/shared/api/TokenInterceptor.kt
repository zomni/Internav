package com.internav.shared.api

import android.content.Context
import com.internav.shared.model.RefreshRequest
import com.internav.shared.model.TokenResponse
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import retrofit2.Retrofit
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class TokenManager {
    var accessToken: String? = null
        private set
    var refreshToken: String? = null
        private set
    private val lock = ReentrantLock()

    @Volatile
    private var appContext: Context? = null

    fun attach(context: Context) {
        appContext = context.applicationContext
    }

    fun getValidToken(): String? = lock.withLock { accessToken }

    fun updateTokens(access: String, refresh: String) = lock.withLock {
        accessToken = access
        refreshToken = refresh
        persistLocked()
    }

    fun restoreFromPrefs() {
        val ctx = appContext ?: return
        lock.withLock {
            val prefs = ctx.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
            accessToken = prefs.getString("access_token", null)
            refreshToken = prefs.getString("refresh_token", null)
        }
    }

    fun clear() {
        lock.withLock {
            accessToken = null
            refreshToken = null
        }
        val ctx = appContext ?: return
        ctx.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
            .edit()
            .remove("access_token")
            .remove("refresh_token")
            .apply()
    }

    private fun persistLocked() {
        val ctx = appContext ?: return
        ctx.getSharedPreferences("internav_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString("access_token", accessToken)
            .putString("refresh_token", refreshToken)
            .apply()
    }
}

class TokenInterceptor(
    private val tokenManager: TokenManager,
    private val retrofit: Retrofit
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val token = tokenManager.getValidToken()

        val request = if (token != null) {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else original

        val response = chain.proceed(request)

        if (response.code == 401 && tokenManager.refreshToken != null) {
            synchronized(this) {
                val refreshed = runBlocking {
                    try {
                        val api = retrofit.create(ApiService::class.java)
                        val refreshResp = api.refreshToken(
                            RefreshRequest(refreshToken = tokenManager.refreshToken!!)
                        )
                        if (refreshResp.isSuccessful) {
                            val body = refreshResp.body()
                            if (body?.success == true && body.data != null) {
                                tokenManager.updateTokens(
                                    body.data.accessToken,
                                    body.data.refreshToken
                                )
                                true
                            } else false
                        } else {
                            tokenManager.clear()
                            false
                        }
                    } catch (_: Exception) {
                        false
                    }
                }

                if (refreshed) {
                    response.close()
                    val newRequest = original.newBuilder()
                        .header("Authorization", "Bearer ${tokenManager.accessToken}")
                        .build()
                    return chain.proceed(newRequest)
                }
            }
        }

        return response
    }
}
