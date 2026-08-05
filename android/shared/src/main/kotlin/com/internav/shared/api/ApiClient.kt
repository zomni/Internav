package com.internav.shared.api

import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {

    private var baseUrl: String = ""
    private var retrofit: Retrofit? = null
    private var apiService: ApiService? = null
    val tokenManager = TokenManager()

    val isInitialized: Boolean
        get() = apiService != null

    fun initialize(url: String, context: Context) {
        tokenManager.attach(context)
        baseUrl = url.trimEnd('/') + "/"

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val okHttp = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()

        retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val authOkHttp = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .addInterceptor(TokenInterceptor(tokenManager, retrofit!!))
            .build()

        val authRetrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(authOkHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        apiService = authRetrofit.create(ApiService::class.java)
    }

    fun getService(): ApiService = apiService
        ?: throw IllegalStateException("ApiClient not initialized. Call initialize(url) first.")

    fun getPublicService(): ApiService {
        val publicOkHttp = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BODY })
            .build()

        val publicRetrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(publicOkHttp)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        return publicRetrofit.create(ApiService::class.java)
    }
}
