package com.internav.shared.sync

import android.content.Context
import android.util.Log
import androidx.work.*
import com.internav.shared.api.ApiClient
import com.internav.shared.local.AppDatabase
import java.util.concurrent.TimeUnit

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        private const val TAG = "SyncWorker"
        const val UNIQUE_NAME = "fingerprint_sync"

        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(
                    UNIQUE_NAME,
                    ExistingWorkPolicy.REPLACE,
                    request
                )
        }

        fun schedulePeriodic(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    UNIQUE_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    request
                )
        }

        private fun ensureApiReady(context: Context) {
            ApiClient.ensureReady(context)
        }
    }

    override suspend fun doWork(): Result {
        Log.d(TAG, "Sync worker started")

        return try {
            ensureApiReady(applicationContext)
            val db = AppDatabase.getInstance(applicationContext)
            val syncManager = SyncManager(db.pendingFingerprintDao())

            when (val result = syncManager.syncPending()) {
                is SyncResult.NoOp -> {
                    Log.d(TAG, "No pending fingerprints to sync")
                    Result.success()
                }
                is SyncResult.Completed -> {
                    Log.d(TAG, "Sync completed: ${result.successCount} success, ${result.failCount} failed")
                    if (result.failCount > 0) Result.retry() else Result.success()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Sync worker failed", e)
            Result.retry()
        }
    }
}

