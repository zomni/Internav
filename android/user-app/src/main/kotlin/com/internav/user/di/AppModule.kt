package com.internav.user.di

import android.content.Context
import com.internav.shared.local.AppDatabase
import com.internav.shared.local.CachedModelDao
import com.internav.shared.local.CachedCellDao
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
            "internav_user_db"
        ).fallbackToDestructiveMigration().build()
    }

    @Provides
    fun provideCachedModelDao(db: AppDatabase): CachedModelDao {
        return db.cachedModelDao()
    }

    @Provides
    fun provideCachedCellDao(db: AppDatabase): CachedCellDao {
        return db.cachedCellDao()
    }
}
