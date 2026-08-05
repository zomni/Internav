-keepattributes Signature
-keep class com.internav.shared.model.** { *; }
-keepclassmembers class com.internav.shared.model.** { *; }
-keep class com.google.gson.** { *; }
-keepclassmembers,allowobfuscation class * {
  @com.google.gson.annotations.SerializedName <fields>;
}
-keep class * extends androidx.room.RoomDatabase
