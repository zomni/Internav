-keepattributes Signature
-keepattributes *Annotation*

# Retrofit
-keep class com.internav.shared.model.** { *; }
-keepclassmembers class com.internav.shared.model.** { *; }

# Gson
-keep class com.google.gson.** { *; }
-keepclassmembers,allowobfuscation class * {
  @com.google.gson.annotations.SerializedName <fields>;
}

# Room
-keep class * extends androidx.room.RoomDatabase
