package com.internav.capture

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.internav.shared.api.ApiClient
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class InternavCaptureApp : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        val prefs = getSharedPreferences("internav_prefs", MODE_PRIVATE)
        val savedUrl = prefs.getString("server_url", null)
        if (savedUrl != null) {
            ApiClient.initialize(savedUrl, this)
            ApiClient.tokenManager.restoreFromPrefs()
        }
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}
