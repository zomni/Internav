package com.internav.shared.sync

import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.internav.shared.api.ApiClient
import com.internav.shared.local.PendingFingerprintDao
import com.internav.shared.local.PendingFingerprintEntity
import com.internav.shared.model.FingerprintRequest
import com.internav.shared.model.ObservationRequest
import kotlinx.coroutines.*

class SyncManager(
    private val dao: PendingFingerprintDao,
    private val gson: Gson = Gson()
) {
    companion object {
        private const val TAG = "SyncManager"
        private const val MAX_RETRIES = 5
        private const val BASE_DELAY_MS = 30_000L
    }

    suspend fun syncPending(): SyncResult {
        val pending = dao.getPendingFingerprints()
        val failed = dao.getFailedFingerprintsReadyForRetry(System.currentTimeMillis())
        val toUpload = pending + failed

        if (toUpload.isEmpty()) return SyncResult.NoOp

        var successCount = 0
        var failCount = 0

        for (fp in toUpload) {
            when (val result = uploadSingle(fp)) {
                is UploadResult.Success -> {
                    dao.markCompleted(fp.id, serverId = result.serverId)
                    successCount++
                }
                is UploadResult.Failure -> {
                    val nextRetry = if (fp.retryCount + 1 < MAX_RETRIES) {
                        System.currentTimeMillis() + BASE_DELAY_MS * (1L shl (fp.retryCount + 1))
                    } else null
                    dao.markFailed(fp.id, nextRetryAt = nextRetry)
                    failCount++
                    if (fp.retryCount + 1 >= MAX_RETRIES) {
                        Log.w(TAG, "Fingerprint ${fp.id} exceeded max retries")
                    }
                }
            }
        }

        return SyncResult.Completed(successCount, failCount)
    }

    private suspend fun uploadSingle(fp: PendingFingerprintEntity): UploadResult {
        return try {
            dao.markUploading(fp.id)

            val observations: List<ObservationRequest> = gson.fromJson(
                fp.observationsJson,
                object : TypeToken<List<ObservationRequest>>() {}.type
            )

            val request = FingerprintRequest(
                cellId = fp.cellId,
                deviceId = fp.deviceId,
                capturedAt = fp.capturedAt,
                sampleNumber = fp.sampleNumber,
                orientation = fp.orientation,
                notes = fp.notes,
                observations = observations
            )

            val response = ApiClient.getService().createFingerprint(fp.campaignId, request)

            if (response.isSuccessful && response.body()?.success == true) {
                val body = response.body()!!
                UploadResult.Success(body.data!!.id)
            } else {
                when (response.code()) {
                    409, 422 -> {
                        Log.w(TAG, "Fingerprint ${fp.id} rejected (${response.code()}), discarding")
                        UploadResult.Success("discarded")
                    }
                    else -> UploadResult.Failure
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Upload failed for fingerprint ${fp.id}", e)
            UploadResult.Failure
        }
    }

    suspend fun enqueueFingerprint(
        campaignId: String,
        cellId: String,
        deviceId: String,
        capturedAt: String,
        sampleNumber: Int,
        orientation: Double?,
        notes: String?,
        observations: List<ObservationRequest>
    ): Long {
        val entity = PendingFingerprintEntity(
            campaignId = campaignId,
            cellId = cellId,
            deviceId = deviceId,
            capturedAt = capturedAt,
            sampleNumber = sampleNumber,
            orientation = orientation,
            notes = notes,
            observationsJson = gson.toJson(observations),
            status = "Pending",
            retryCount = 0
        )
        return dao.insert(entity)
    }

    suspend fun getPendingCount(): Int = dao.getPendingCount()
}

sealed class UploadResult {
    data class Success(val serverId: String) : UploadResult()
    data object Failure : UploadResult()
}

sealed class SyncResult {
    data object NoOp : SyncResult()
    data class Completed(val successCount: Int, val failCount: Int) : SyncResult()
}
