package com.internav.capture.navigation

object NavRoutes {
    const val LOGIN = "login"
    const val ORGANIZATIONS = "organizations"
    const val SITES = "sites/{orgId}"
    const val BUILDINGS = "buildings/{siteId}"
    const val FLOORS = "floors/{buildingId}"
    const val CAMPAIGNS = "campaigns/{floorId}"
    const val CELL_SELECTION = "cells/{campaignId}/{floorId}"
    const val CAPTURE = "capture/{campaignId}/{floorId}/{cellId}/{cellLabel}"
    const val REVIEW = "review/{fingerprintId}"
    const val SYNC_STATUS = "sync"

    fun sites(orgId: String) = "sites/$orgId"
    fun buildings(siteId: String) = "buildings/$siteId"
    fun floors(buildingId: String) = "floors/$buildingId"
    fun campaigns(floorId: String) = "campaigns/$floorId"
    fun cellSelection(campaignId: String, floorId: String) = "cells/$campaignId/$floorId"
    fun capture(campaignId: String, floorId: String, cellId: String, cellLabel: String) = "capture/$campaignId/$floorId/$cellId/$cellLabel"
    fun review(fingerprintId: String) = "review/$fingerprintId"
}
