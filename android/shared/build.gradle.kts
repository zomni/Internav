plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.internav.shared"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    api(libs.retrofit)
    api(libs.retrofit.gson)
    api(libs.okhttp)
    api(libs.okhttp.logging)
    api(libs.room.runtime)
    api(libs.room.ktx)
    api(libs.hilt.android)
    api(libs.coroutines.android)
    api(libs.work.runtime)

    ksp(libs.room.compiler)
    ksp(libs.hilt.compiler)
}
