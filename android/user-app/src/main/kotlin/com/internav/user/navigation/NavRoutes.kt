package com.internav.user.navigation

object NavRoutes {
    const val LOGIN = "login"
    const val ORGANIZATIONS = "organizations"
    const val SITES = "sites/{orgId}"
    const val BUILDINGS = "buildings/{siteId}"
    const val MAP = "map/{buildingId}"

    fun sites(orgId: String) = "sites/$orgId"
    fun buildings(siteId: String) = "buildings/$siteId"
    fun map(buildingId: String) = "map/$buildingId"
}
