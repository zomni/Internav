package com.internav.shared.api

import com.internav.shared.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<ApiEnvelope<LoginResponse>>

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(@Body request: RefreshRequest): Response<ApiEnvelope<TokenResponse>>

    @GET("api/v1/organizations")
    suspend fun listOrganizations(): Response<ApiEnvelope<List<Organization>>>

    @GET("api/v1/sites")
    suspend fun listSites(@Query("organization_id") organizationId: String? = null): Response<ApiEnvelope<List<Site>>>

    @GET("api/v1/buildings")
    suspend fun listBuildings(@Query("site_id") siteId: String? = null): Response<ApiEnvelope<List<Building>>>

    @GET("api/v1/floors")
    suspend fun listFloors(@Query("building_id") buildingId: String? = null): Response<ApiEnvelope<List<Floor>>>

    @GET("api/v1/floors/{floorId}")
    suspend fun getFloor(@Path("floorId") floorId: String): Response<ApiEnvelope<Floor>>

    @GET("api/v1/floors/{floorId}/floor-plans")
    suspend fun listFloorPlans(@Path("floorId") floorId: String): Response<ApiEnvelope<List<FloorPlan>>>

    @GET("api/v1/floor-plans/{floorId}/image")
    @Streaming
    suspend fun downloadFloorPlanImage(@Path("floorId") floorId: String): Response<okhttp3.ResponseBody>

    @GET("api/v1/floors/{floorId}/grids")
    suspend fun listGrids(@Path("floorId") floorId: String): Response<ApiEnvelope<List<Grid>>>

    @GET("api/v1/grids/{gridId}/cells")
    suspend fun listCells(@Path("gridId") gridId: String): Response<ApiEnvelope<List<Cell>>>

    @GET("api/v1/floors/{floorId}/campaigns")
    suspend fun listCampaigns(@Path("floorId") floorId: String): Response<ApiEnvelope<List<Campaign>>>

    @GET("api/v1/campaigns/{campaignId}")
    suspend fun getCampaign(@Path("campaignId") campaignId: String): Response<ApiEnvelope<Campaign>>

    @PATCH("api/v1/campaigns/{campaignId}/begin-collecting")
    suspend fun beginCollecting(@Path("campaignId") campaignId: String): Response<ApiEnvelope<Campaign>>

    @PATCH("api/v1/campaigns/{campaignId}/pause")
    suspend fun pauseCampaign(@Path("campaignId") campaignId: String): Response<ApiEnvelope<Campaign>>

    @PATCH("api/v1/campaigns/{campaignId}/resume")
    suspend fun resumeCampaign(@Path("campaignId") campaignId: String): Response<ApiEnvelope<Campaign>>

    @PATCH("api/v1/campaigns/{campaignId}/complete")
    suspend fun completeCampaign(@Path("campaignId") campaignId: String): Response<ApiEnvelope<Campaign>>

    @POST("api/v1/campaigns/{campaignId}/fingerprints")
    suspend fun createFingerprint(
        @Path("campaignId") campaignId: String,
        @Body request: FingerprintRequest
    ): Response<ApiEnvelope<FingerprintResponse>>

    @GET("api/v1/campaigns/{campaignId}/fingerprints")
    suspend fun listFingerprints(@Path("campaignId") campaignId: String): Response<ApiEnvelope<List<FingerprintResponse>>>

    @GET("api/v1/floors/{floorId}/model-update")
    suspend fun checkModelUpdate(@Path("floorId") floorId: String): Response<ApiEnvelope<ModelUpdateResponse>>

    @GET("api/v1/models/{modelId}/download")
    @Streaming
    suspend fun downloadModel(@Path("modelId") modelId: String): Response<okhttp3.ResponseBody>

    @GET("api/v1/models/{modelId}/mobile-bundle")
    @Streaming
    suspend fun downloadMobileBundle(@Path("modelId") modelId: String): Response<okhttp3.ResponseBody>

    @GET("api/v1/models/{modelId}")
    suspend fun getModel(@Path("modelId") modelId: String): Response<ApiEnvelope<ModelResponse>>

    @GET("api/v1/floors/{floorId}/models")
    suspend fun listModelsByFloor(@Path("floorId") floorId: String): Response<ApiEnvelope<List<ModelResponse>>>

    @GET("api/v1/grids/{gridId}/cells")
    suspend fun listCellsByGrid(@Path("gridId") gridId: String): Response<ApiEnvelope<List<Cell>>>

    @POST("api/v1/inference")
    suspend fun onlineInference(@Body request: InferenceRequest): Response<ApiEnvelope<InferenceResponse>>
}
