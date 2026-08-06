package com.internav.capture.di

import android.content.Context
import com.internav.shared.local.AppDatabase
import com.internav.shared.local.PendingFingerprintDao
import com.internav.shared.sync.SyncManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase {
        return androidx.room.Room.databaseBuilder(
            context.applicationContext,
            AppDatabase::class.java,
            "internav_capture_db"
        ).addMigrations(AppDatabase.MIGRATION_2_3).build()
    }

    @Provides
    fun providePendingFingerprintDao(db: AppDatabase): PendingFingerprintDao {
        return db.pendingFingerprintDao()
    }

    @Provides
    @Singleton
    fun provideSyncManager(dao: PendingFingerprintDao): SyncManager {
        return SyncManager(dao)
    }
}
