package com.internav.shared.local

import android.content.Context
import androidx.room.*
import androidx.room.migration.Migration

@Entity(tableName = "pending_fingerprints")
data class PendingFingerprintEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "campaign_id") val campaignId: String,
    @ColumnInfo(name = "cell_id") val cellId: String,
    @ColumnInfo(name = "cell_label") val cellLabel: String? = null,
    @ColumnInfo(name = "device_id") val deviceId: String,
    @ColumnInfo(name = "captured_at") val capturedAt: String,
    @ColumnInfo(name = "sample_number") val sampleNumber: Int,
    val orientation: Double?,
    val notes: String?,
    @ColumnInfo(name = "observations_json") val observationsJson: String,
    val status: String = "Pending",
    @ColumnInfo(name = "retry_count") val retryCount: Int = 0,
    @ColumnInfo(name = "next_retry_at") val nextRetryAt: Long? = null,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "server_id") val serverId: String? = null
)

@Dao
interface PendingFingerprintDao {

    @Query("SELECT * FROM pending_fingerprints WHERE status = 'Pending' ORDER BY created_at ASC")
    suspend fun getPendingFingerprints(): List<PendingFingerprintEntity>

    @Query("SELECT * FROM pending_fingerprints ORDER BY created_at ASC")
    suspend fun getAllFingerprints(): List<PendingFingerprintEntity>

    @Query("SELECT * FROM pending_fingerprints WHERE status = 'Uploading'")
    suspend fun getUploadingFingerprints(): List<PendingFingerprintEntity>

    @Query("SELECT COALESCE(MAX(sample_number), 0) FROM pending_fingerprints WHERE cell_id = :cellId")
    suspend fun getMaxSampleNumberForCell(cellId: String): Int

    @Query("UPDATE pending_fingerprints SET cell_label = :label WHERE cell_id = :cellId AND (cell_label IS NULL OR cell_label != :label)")
    suspend fun updateCellLabel(cellId: String, label: String)

    @Query("SELECT * FROM pending_fingerprints WHERE status = 'Failed' AND (next_retry_at IS NULL OR next_retry_at <= :now)")
    suspend fun getFailedFingerprintsReadyForRetry(now: Long): List<PendingFingerprintEntity>

    @Query("SELECT COUNT(*) FROM pending_fingerprints WHERE status = 'Pending' OR status = 'Failed'")
    suspend fun getPendingCount(): Int

    @Insert
    suspend fun insert(entity: PendingFingerprintEntity): Long

    @Update
    suspend fun update(entity: PendingFingerprintEntity)

    @Query("UPDATE pending_fingerprints SET status = :status, server_id = :serverId WHERE id = :id")
    suspend fun markCompleted(id: Long, status: String = "Completed", serverId: String?)

    @Query("UPDATE pending_fingerprints SET status = 'Failed', retry_count = retry_count + 1, next_retry_at = :nextRetryAt WHERE id = :id")
    suspend fun markFailed(id: Long, nextRetryAt: Long?)

    @Query("UPDATE pending_fingerprints SET status = 'Rejected' WHERE id = :id")
    suspend fun markRejected(id: Long)

    @Query("UPDATE pending_fingerprints SET status = 'Uploading' WHERE id = :id")
    suspend fun markUploading(id: Long)

    @Query("DELETE FROM pending_fingerprints WHERE status = 'Completed'")
    suspend fun deleteCompleted()

    @Query("DELETE FROM pending_fingerprints WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Query("SELECT cell_id, COUNT(*) as cnt FROM pending_fingerprints WHERE campaign_id = :campaignId GROUP BY cell_id")
    suspend fun getCaptureCountByCellId(campaignId: String): List<CellCaptureCount>
}

data class CellCaptureCount(
    @ColumnInfo(name = "cell_id") val cellId: String,
    val cnt: Int
)

@Entity(tableName = "cached_models")
data class CachedModelEntity(
    @PrimaryKey @ColumnInfo(name = "floor_id") val floorId: String,
    @ColumnInfo(name = "model_id") val modelId: String,
    val version: Int,
    val algorithm: String,
    val checksum: String?,
    @ColumnInfo(name = "model_path") val modelPath: String?,
    @ColumnInfo(name = "schema_path") val schemaPath: String?,
    @ColumnInfo(name = "cells_json") val cellsJson: String?,
    @ColumnInfo(name = "downloaded_at") val downloadedAt: Long = System.currentTimeMillis()
)

@Dao
interface CachedModelDao {
    @Query("SELECT * FROM cached_models WHERE floor_id = :floorId")
    suspend fun getModelForFloor(floorId: String): CachedModelEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdate(model: CachedModelEntity)

    @Query("DELETE FROM cached_models WHERE floor_id = :floorId")
    suspend fun deleteModelForFloor(floorId: String)

    @Query("SELECT * FROM cached_models")
    suspend fun getAllCachedModels(): List<CachedModelEntity>
}

@Entity(tableName = "cached_cells")
data class CachedCellEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "grid_id") val gridId: String,
    @ColumnInfo(name = "row") val row: Int,
    @ColumnInfo(name = "col") val column: Int,
    @ColumnInfo(name = "center_x") val centerX: Double,
    @ColumnInfo(name = "center_y") val centerY: Double,
    val walkable: Boolean,
    @ColumnInfo(name = "floor_id") val floorId: String
)

@Dao
interface CachedCellDao {
    @Query("SELECT * FROM cached_cells WHERE floor_id = :floorId")
    suspend fun getCellsForFloor(floorId: String): List<CachedCellEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(cells: List<CachedCellEntity>)

    @Query("DELETE FROM cached_cells WHERE floor_id = :floorId")
    suspend fun deleteCellsForFloor(floorId: String)
}

@Database(
    entities = [
        PendingFingerprintEntity::class,
        CachedModelEntity::class,
        CachedCellEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun pendingFingerprintDao(): PendingFingerprintDao
    abstract fun cachedModelDao(): CachedModelDao
    abstract fun cachedCellDao(): CachedCellDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE pending_fingerprints ADD COLUMN cell_label TEXT")
            }
        }

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "internav_capture_db"
                ).addMigrations(MIGRATION_2_3).build().also { INSTANCE = it }
            }
        }
    }
}
