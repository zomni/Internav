package com.internav.user.viewmodel

import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.wifi.WifiManager
import android.os.Looper
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.internav.shared.api.ApiClient
import com.internav.shared.inference.InferenceEngine
import com.internav.shared.inference.InferenceResult
import com.internav.shared.inference.ReferenceVector
import com.internav.shared.inference.RssiObservation
import com.internav.shared.local.AppDatabase
import com.internav.shared.local.CachedCellEntity
import com.internav.shared.local.CachedModelEntity
import com.internav.shared.model.FeatureSchema
import com.internav.shared.model.Floor
import com.internav.shared.model.FloorPlan
import com.internav.shared.model.ModelInfo
import com.internav.user.util.Prefs
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.IOException
import java.security.MessageDigest
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class PositionSource { MODEL, GPS, NONE }

private const val MAX_LIVE_ACCURACY = 60f
private const val MAX_LIVE_AGE_MS = 30_000L
private const val MAX_SEED_ACCURACY = 80f
private const val MAX_SEED_AGE_MS = 5 * 60_000L

data class GpsPosition(
    val lat: Double,
    val lng: Double,
    val accuracy: Float,
    val time: Long
)

data class MapUiState(
    val isLoading: Boolean = true,
    val buildingName: String? = null,
    val floors: List<Floor> = emptyList(),
    val activeFloorId: String? = null,
    val floorPlan: FloorPlan? = null,
    val cells: List<CachedCellEntity> = emptyList(),
    val gridCellSize: Float = 0f,
    val result: InferenceResult? = null,
    val lastScan: List<RssiObservation> = emptyList(),
    val positionSource: PositionSource = PositionSource.NONE,
    val gpsPosition: GpsPosition? = null,
    val autoFloor: Boolean = true,
    val error: String? = null
)

private data class MobileBundle(
    @SerializedName("feature_schema") val featureSchema: MobileFeatureSchema,
    val references: List<BundleReference>
)

private data class MobileFeatureSchema(
    @SerializedName("bssid_vocabulary") val bssidVocabulary: List<String>,
    @SerializedName("missing_ap_value") val missingApValue: Double? = 0.0
)

private data class BundleReference(
    @SerializedName("cell_id") val cellId: String,
    val vector: List<Double>
)

@HiltViewModel
class MapViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val database: AppDatabase
) : ViewModel() {

    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state

    private val engines = mutableMapOf<String, InferenceEngine>()
    private var wifiManager: WifiManager? = null
    private var locationManager: LocationManager? = null
    private var scanJob: Job? = null
    private var gpsJob: Job? = null
    private var gpsListener: LocationListener? = null
    private var currentBuildingId: String? = null

    fun initialize(buildingId: String) {
        if (currentBuildingId == buildingId) return
        currentBuildingId = buildingId
        wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        locationManager = context.applicationContext.getSystemService(Context.LOCATION_SERVICE) as? LocationManager

        _state.value = MapUiState(isLoading = true)

        viewModelScope.launch {
            try {
                val siteId = Prefs.lastSiteId(context)
                val buildingName = siteId?.let { sid ->
                    runCatching {
                        ApiClient.getService().listBuildings(sid).body()?.data
                            ?.firstOrNull { it.id == buildingId }?.name
                    }.getOrNull()
                }

                val floorsResp = ApiClient.getService().listFloors(buildingId)
                val floors = floorsResp.body()?.data ?: emptyList()
                if (floors.isEmpty()) {
                    _state.value = _state.value.copy(isLoading = false, error = "No floors for this building")
                    return@launch
                }
                _state.value = _state.value.copy(isLoading = false, buildingName = buildingName, floors = floors)

                val defaultFloor = floors.minByOrNull { it.level } ?: floors.first()
                loadFloor(defaultFloor.id)

                floors.forEach { floor ->
                    ensureEngineForFloor(floor.id)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun selectFloor(floorId: String) {
        _state.value = _state.value.copy(autoFloor = false)
        viewModelScope.launch { loadFloor(floorId) }
    }

    fun enableAutoFloor() {
        _state.value = _state.value.copy(autoFloor = true)
    }

    fun startScanning() {
        if (scanJob?.isActive == true) return
        scanJob = viewModelScope.launch {
            while (isActive) {
                scanOnce()
                delay(2000)
            }
        }
    }

    fun stopScanning() {
        scanJob?.cancel()
        scanJob = null
        stopGps()
    }

    private suspend fun loadFloor(floorId: String) {
        val current = _state.value
        if (current.activeFloorId == floorId && current.cells.isNotEmpty()) return
        _state.value = current.copy(activeFloorId = floorId, floorPlan = null, result = null)

        try {
            val planResp = ApiClient.getService().listFloorPlans(floorId)
            val floorPlan = planResp.body()?.data?.firstOrNull()
            val gridResp = ApiClient.getService().listGrids(floorId)
            val grids = gridResp.body()?.data ?: emptyList()
            val activeGrid = grids.firstOrNull {
                it.status.equals("Active", ignoreCase = true)
            } ?: grids.firstOrNull()

            val allCells = mutableListOf<CachedCellEntity>()
            if (activeGrid != null) {
                val cellsResp = ApiClient.getService().listCells(activeGrid.id)
                val cells = cellsResp.body()?.data ?: emptyList()
                for (cell in cells) {
                    allCells.add(
                        CachedCellEntity(
                            id = cell.id,
                            gridId = cell.gridId,
                            row = cell.row,
                            column = cell.column,
                            centerX = cell.centerX,
                            centerY = cell.centerY,
                            walkable = cell.walkable,
                            floorId = floorId
                        )
                    )
                }
            }
            database.cachedCellDao().deleteCellsForFloor(floorId)
            database.cachedCellDao().insertAll(allCells)
            val stored = database.cachedCellDao().getCellsForFloor(floorId)

            _state.value = _state.value.copy(
                floorPlan = floorPlan,
                cells = stored,
                gridCellSize = activeGrid?.cellSize?.toFloat() ?: 0f
            )
        } catch (e: Exception) {
            val stored = database.cachedCellDao().getCellsForFloor(floorId)
            _state.value = _state.value.copy(cells = stored, error = e.message)
        }
    }

    private suspend fun ensureEngineForFloor(floorId: String) {
        if (engines[floorId] != null) return
        val cached = database.cachedModelDao().getModelForFloor(floorId)
        try {
            val updateResp = ApiClient.getService().checkModelUpdate(floorId)
            val update = updateResp.body()?.data
            val model = update?.model
            val needsDownload = update?.updateAvailable == true || cached == null
            if (needsDownload && model != null) {
                downloadAndActivateBundle(floorId, model)
            } else if (cached != null) {
                buildEngineFromBundle(cached.cellsJson, floorId)
            }
        } catch (e: Exception) {
            if (cached != null) {
                buildEngineFromBundle(cached.cellsJson, floorId)
            }
        }
    }

    private suspend fun downloadAndActivateBundle(floorId: String, model: ModelInfo) {
        val resp = ApiClient.getService().downloadMobileBundle(model.id)
        if (!resp.isSuccessful) throw IOException("Model download failed (${resp.code()})")
        val body = resp.body() ?: throw IOException("Empty model response")
        val bytes = body.bytes()

        val expected = resp.headers()["X-Model-Checksum"]
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
        val actual = digest.joinToString("") { "%02x".format(it) }
        if (expected != null && !expected.equals(actual, ignoreCase = true)) {
            throw IOException("Model checksum mismatch")
        }

        val json = String(bytes, Charsets.UTF_8)
        if (!buildEngineFromBundle(json, floorId)) {
            throw IOException("Downloaded model could not be activated")
        }

        database.cachedModelDao().insertOrUpdate(
            CachedModelEntity(
                floorId = floorId,
                modelId = model.id,
                version = model.version,
                algorithm = model.algorithm,
                checksum = model.checksum,
                modelPath = null,
                schemaPath = null,
                cellsJson = json,
                downloadedAt = System.currentTimeMillis()
            )
        )
    }

    private suspend fun buildEngineFromBundle(bundleJson: String?, floorId: String): Boolean {
        if (bundleJson.isNullOrBlank()) return false
        return try {
            val bundle = Gson().fromJson(bundleJson, MobileBundle::class.java)
            val cells = database.cachedCellDao().getCellsForFloor(floorId)
            val cellById = cells.associateBy { it.id }

            val refVectors = bundle.references.mapNotNull { ref ->
                val cell = cellById[ref.cellId] ?: return@mapNotNull null
                ReferenceVector(
                    cellId = cell.id,
                    centerX = cell.centerX,
                    centerY = cell.centerY,
                    vector = ref.vector.toDoubleArray()
                )
            }
            if (refVectors.isEmpty()) return false

            val schema = FeatureSchema(
                bssidVocabulary = bundle.featureSchema.bssidVocabulary,
                featureCount = bundle.featureSchema.bssidVocabulary.size,
                normalization = "min_max_100",
                missingApValue = bundle.featureSchema.missingApValue ?: 0.0
            )
            engines[floorId] = InferenceEngine(referenceVectors = refVectors, featureSchema = schema, k = 3)
            true
        } catch (_: Exception) {
            false
        }
    }

    private suspend fun scanOnce() = withContext(Dispatchers.IO) {
        try {
            val mgr = wifiManager ?: return@withContext
            val observations = mutableListOf<RssiObservation>()

            if (mgr.isWifiEnabled) {
                runCatching { mgr.startScan() }
                delay(1500)
                observations.addAll(
                    mgr.scanResults.map { RssiObservation(bssid = it.BSSID, rssi = it.level) }
                )
            }
            val topObs = observations.take(30)
            val current = _state.value

            if (current.autoFloor) {
                val candidates = engines.mapNotNull { (floorId, eng) ->
                    val res = eng.estimatePosition(topObs)
                    if (res.predictedCellId != null) floorId to res else null
                }
                if (candidates.isNotEmpty()) {
                    val (bestFloorId, bestResult) = candidates.maxByOrNull { it.second.confidence }!!
                    if (bestFloorId != current.activeFloorId) {
                        loadFloor(bestFloorId)
                    }
                    _state.value = _state.value.copy(
                        activeFloorId = bestFloorId,
                        result = bestResult,
                        lastScan = topObs,
                        positionSource = PositionSource.MODEL,
                        gpsPosition = null
                    )
                    stopGps()
                    return@withContext
                }
            } else {
                val activeId = current.activeFloorId
                val eng = activeId?.let { engines[it] }
                if (eng != null) {
                    val res = eng.estimatePosition(topObs)
                    if (res.predictedCellId != null) {
                        _state.value = _state.value.copy(
                            result = res,
                            lastScan = topObs,
                            positionSource = PositionSource.MODEL,
                            gpsPosition = null
                        )
                        stopGps()
                        return@withContext
                    }
                }
            }

            _state.value = _state.value.copy(lastScan = topObs, positionSource = PositionSource.GPS)
            startGpsIfNeeded()
        } catch (_: Exception) {
        }
    }

    private fun startGpsIfNeeded() {
        if (gpsJob?.isActive == true) return
        val lm = locationManager ?: return
        registerGpsListener(lm)
        gpsJob = viewModelScope.launch {
            val loc = bestLastKnownLocation()
            if (loc != null && isUsableSeed(loc) && isNewerThanCurrent(loc)) {
                publishLocation(loc)
            }
        }
    }

    private fun registerGpsListener(lm: LocationManager) {
        if (gpsListener != null) return
        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                if (isGoodFix(location) && isNewerThanCurrent(location)) {
                    publishLocation(location)
                }
            }
        }
        gpsListener = listener
        val providers = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER
        )
        for (provider in providers) {
            if (lm.getProvider(provider) == null) continue
            try {
                lm.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
            } catch (_: SecurityException) {
            } catch (_: IllegalArgumentException) {
            }
        }
    }

    private fun stopGps() {
        gpsJob?.cancel()
        gpsJob = null
        val lm = locationManager
        val listener = gpsListener
        if (lm != null && listener != null) {
            try {
                lm.removeUpdates(listener)
            } catch (_: SecurityException) {
            }
        }
        gpsListener = null
    }

    private fun publishLocation(loc: Location) {
        _state.value = _state.value.copy(
            gpsPosition = GpsPosition(
                lat = loc.latitude,
                lng = loc.longitude,
                accuracy = loc.accuracy,
                time = loc.time
            )
        )
    }

    private fun isGoodFix(loc: Location): Boolean =
        loc.hasAccuracy() &&
            loc.accuracy in 1f..MAX_LIVE_ACCURACY &&
            System.currentTimeMillis() - loc.time < MAX_LIVE_AGE_MS

    private fun isUsableSeed(loc: Location): Boolean =
        loc.hasAccuracy() &&
            loc.accuracy in 1f..MAX_SEED_ACCURACY &&
            System.currentTimeMillis() - loc.time < MAX_SEED_AGE_MS

    private fun isNewerThanCurrent(loc: Location): Boolean {
        val current = _state.value.gpsPosition ?: return true
        return loc.time >= current.time
    }

    private fun bestLastKnownLocation(): Location? {
        val lm = locationManager ?: return null
        var best: Location? = null
        val providers = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER
        )
        for (provider in providers) {
            val loc = try {
                lm.getLastKnownLocation(provider)
            } catch (_: SecurityException) {
                null
            } catch (_: IllegalArgumentException) {
                null
            } ?: continue
            if (!loc.hasAccuracy()) continue
            if (best == null || isBetter(loc, best)) best = loc
        }
        return best
    }

    private fun isBetter(candidate: Location, current: Location): Boolean {
        val cAge = System.currentTimeMillis() - candidate.time
        val bAge = System.currentTimeMillis() - current.time
        val cFresh = cAge < MAX_SEED_AGE_MS
        val bFresh = bAge < MAX_SEED_AGE_MS
        if (cFresh != bFresh) return cFresh
        return candidate.accuracy < current.accuracy
    }
}
