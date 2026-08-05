package com.internav.user.util

import android.content.Context
import android.content.SharedPreferences

object Prefs {
    const val NAME = "internav_prefs"
    const val KEY_SERVER_URL = "server_url"
    const val KEY_LAST_ORG = "last_organization_id"
    const val KEY_LAST_SITE = "last_site_id"
    const val KEY_LAST_BUILDING = "last_building_id"

    fun get(context: Context): SharedPreferences =
        context.getSharedPreferences(NAME, Context.MODE_PRIVATE)

    fun lastBuildingId(context: Context): String? =
        get(context).getString(KEY_LAST_BUILDING, null)

    fun lastSiteId(context: Context): String? =
        get(context).getString(KEY_LAST_SITE, null)

    fun saveOrganization(context: Context, orgId: String) {
        get(context).edit().putString(KEY_LAST_ORG, orgId).apply()
    }

    fun saveSite(context: Context, siteId: String) {
        get(context).edit().putString(KEY_LAST_SITE, siteId).apply()
    }

    fun saveBuilding(context: Context, buildingId: String) {
        get(context).edit().putString(KEY_LAST_BUILDING, buildingId).apply()
    }
}
