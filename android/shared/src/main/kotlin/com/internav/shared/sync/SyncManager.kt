package com.internav.shared.sync

import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.internav.shared.api.ApiClient
import com.internav.shared.local.PendingFingerprintDao
import com.internav.shared.local.PendingFingerprintEntity
import com.internav.shared.model.ApiEnvelope
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
        var rejectedCount = 0
        var failCount = 0
        val errors = mutableListOf<String>()

        for (fp in toUpload) {
            when (val result = uploadSingle(fp)) {
                is UploadResult.Success -> {
                    dao.markCompleted(fp.id, serverId = result.serverId)
                    successCount++
                }
                is UploadResult.Rejected -> {
                    dao.markRejected(fp.id)
                    rejectedCount++
                    val reason = result.reason ?: "rejected by server"
                    errors += "Sample ${fp.sampleNumber} (${fp.cellLabel ?: fp.cellId}): $reason"
                    Log.w(TAG, "Fingerprint ${fp.id} rejected: $reason")
                }
                is UploadResult.Failure -> {
                    val nextRetry = if (fp.retryCount + 1 < MAX_RETRIES) {
                        System.currentTimeMillis() + BASE_DELAY_MS * (1L shl (fp.retryCount + 1))
                    } else null
                    dao.markFailed(fp.id, nextRetryAt = nextRetry)
                    failCount++
                    val reason = result.reason ?: "unknown error"
                    errors += "Sample ${fp.sampleNumber} (${fp.cellLabel ?: fp.cellId}): $reason"
                    if (fp.retryCount + 1 >= MAX_RETRIES) {
                        Log.w(TAG, "Fingerprint ${fp.id} exceeded max retries")
                    }
                }
            }
        }

        return SyncResult.Completed(successCount, rejectedCount, failCount, errors)
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
                val detail = response.errorBody()?.string()?.let { parseError(it) }
                when (response.code()) {
                    409, 422 -> UploadResult.Rejected(detail ?: "HTTP ${response.code()}")
                    401 -> UploadResult.Failure(detail ?: "Unauthorized (HTTP 401)")
                    else -> UploadResult.Failure(detail ?: "HTTP ${response.code()}")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Upload failed for fingerprint ${fp.id}", e)
            UploadResult.Failure(e.message ?: "Connection error")
        }
    }

    private fun parseError(body: String): String? {
        return try {
            val env = gson.fromJson(body, ApiEnvelope::class.java)
            env?.message ?: env?.errors?.joinToString("; ")
        } catch (e: Exception) {
            null
        }
    }

    suspend fun enqueueFingerprint(
        campaignId: String,
        cellId: String,
        cellLabel: String?,
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
            cellLabel = cellLabel,
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
    data class Rejected(val reason: String?) : UploadResult()
    data class Failure(val reason: String?) : UploadResult()
}

sealed class SyncResult {
    data object NoOp : SyncResult()
    data class Completed(
        val successCount: Int,
        val rejectedCount: Int,
        val failCount: Int,
        val errors: List<String>
    ) : SyncResult()
}
