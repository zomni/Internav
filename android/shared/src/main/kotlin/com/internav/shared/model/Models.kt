package com.internav.shared.model

import com.google.gson.annotations.SerializedName

data class ApiEnvelope<T>(
    val success: Boolean,
    val data: T?,
    val message: String?,
    val errors: List<String>?,
    val metadata: Map<String, Any>?
)

data class PaginatedResponse<T>(
    val items: List<T>,
    val total: Int,
    val page: Int,
    @SerializedName("page_size") val pageSize: Int
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String,
    val user: User
)

data class RefreshRequest(
    @SerializedName("refresh_token") val refreshToken: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String
)

data class User(
    val id: String,
    val email: String,
    val role: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("organization_id") val organizationId: String?,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
)

data class Organization(
    val id: String,
    val name: String,
    val code: String,
    val description: String?
)

data class Site(
    val id: String,
    @SerializedName("organization_id") val organizationId: String,
    val name: String,
    val code: String,
    val timezone: String,
    val address: String?
)

data class Building(
    val id: String,
    @SerializedName("site_id") val siteId: String,
    val name: String,
    val code: String,
    val description: String?
)

data class Floor(
    val id: String,
    @SerializedName("building_id") val buildingId: String,
    val name: String,
    val level: Int,
    @SerializedName("display_order") val displayOrder: Int
)

data class FloorPlan(
    val id: String,
    @SerializedName("floor_id") val floorId: String,
    @SerializedName("image_path") val imagePath: String,
    val width: Int,
    val height: Int,
    val scale: Double,
    @SerializedName("is_active") val isActive: Boolean
)

data class Grid(
    val id: String,
    @SerializedName("floor_id") val floorId: String,
    val name: String,
    @SerializedName("cell_size") val cellSize: Double,
    val status: String
)

data class Cell(
    val id: String,
    @SerializedName("grid_id") val gridId: String,
    val row: Int,
    val column: Int,
    @SerializedName("center_x") val centerX: Double,
    @SerializedName("center_y") val centerY: Double,
    val walkable: Boolean
)

data class Campaign(
    val id: String,
    @SerializedName("floor_id") val floorId: String,
    val name: String,
    val status: String,
    @SerializedName("started_at") val startedAt: String?,
    @SerializedName("finished_at") val finishedAt: String?,
    @SerializedName("is_deleted") val isDeleted: Boolean
)

data class FingerprintRequest(
    @SerializedName("cell_id") val cellId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("captured_at") val capturedAt: String,
    @SerializedName("sample_number") val sampleNumber: Int,
    val orientation: Double? = null,
    val notes: String? = null,
    val observations: List<ObservationRequest>
)

data class ObservationRequest(
    val bssid: String,
    val ssid: String? = "",
    val rssi: Int,
    val frequency: Int,
    val channel: Int? = 0,
    val band: String? = "",
    val security: String? = ""
)

data class FingerprintResponse(
    val id: String,
    @SerializedName("campaign_id") val campaignId: String,
    @SerializedName("cell_id") val cellId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("captured_at") val capturedAt: String,
    @SerializedName("sample_number") val sampleNumber: Int,
    val observations: List<ObservationResponse>,
    val version: Int
)

data class ObservationResponse(
    val id: String?,
    val bssid: String,
    val ssid: String?,
    val rssi: Int,
    val frequency: Int,
    val channel: Int?,
    val band: String?,
    val security: String?
)

data class ModelUpdateResponse(
    @SerializedName("update_available") val updateAvailable: Boolean,
    val model: ModelInfo?
)

data class ModelInfo(
    val id: String,
    val version: Int,
    val algorithm: String,
    val checksum: String?,
    @SerializedName("published_at") val publishedAt: String?
)

data class ModelResponse(
    val id: String,
    @SerializedName("dataset_id") val datasetId: String,
    @SerializedName("floor_id") val floorId: String,
    val algorithm: String,
    val version: Int,
    val status: String,
    val checksum: String?,
    @SerializedName("published_at") val publishedAt: String?,
    val metrics: Map<String, Double>?,
    @SerializedName("created_at") val createdAt: String?
)

data class InferenceRequest(
    @SerializedName("floor_id") val floorId: String,
    val observations: List<InferenceObservation>
)

data class InferenceObservation(
    val bssid: String,
    val ssid: String? = "",
    val rssi: Int,
    val frequency: Int
)

data class InferenceResponse(
    @SerializedName("predicted_cell_id") val predictedCellId: String?,
    @SerializedName("center_x") val centerX: Double?,
    @SerializedName("center_y") val centerY: Double?,
    val confidence: Double?,
    @SerializedName("candidate_cells") val candidateCells: List<CandidateCell>?,
    @SerializedName("model_version_id") val modelVersionId: String?,
    @SerializedName("inference_time_ms") val inferenceTimeMs: Double?
)

data class CandidateCell(
    @SerializedName("cell_id") val cellId: String,
    val score: Double
)

data class FeatureSchema(
    @SerializedName("bssid_vocabulary") val bssidVocabulary: List<String>,
    @SerializedName("feature_count") val featureCount: Int?,
    val normalization: String?,
    @SerializedName("missing_ap_value") val missingApValue: Double?
)
