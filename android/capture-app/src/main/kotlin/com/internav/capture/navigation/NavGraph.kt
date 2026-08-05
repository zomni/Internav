package com.internav.capture.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.internav.capture.ui.screens.*

@Composable
fun CaptureNavGraph(navController: NavHostController) {
    NavHost(navController = navController, startDestination = NavRoutes.LOGIN) {

        composable(NavRoutes.LOGIN) {
            LoginScreen(onLoginSuccess = {
                navController.navigate(NavRoutes.ORGANIZATIONS) {
                    popUpTo(NavRoutes.LOGIN) { inclusive = true }
                }
            })
        }

        composable(NavRoutes.ORGANIZATIONS) {
            OrganizationSelectionScreen(
                onOrgSelected = { orgId, orgName ->
                    NavState.crumbs.add(orgName)
                    navController.navigate(NavRoutes.sites(orgId))
                },
                onSyncStatus = {
                    navController.navigate(NavRoutes.SYNC_STATUS)
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.SITES,
            arguments = listOf(navArgument("orgId") { type = NavType.StringType })
        ) { backStackEntry ->
            val orgId = backStackEntry.arguments?.getString("orgId") ?: return@composable
            SiteSelectionScreen(
                organizationId = orgId,
                onSiteSelected = { siteId, siteName ->
                    NavState.crumbs.add(siteName)
                    navController.navigate(NavRoutes.buildings(siteId))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.BUILDINGS,
            arguments = listOf(navArgument("siteId") { type = NavType.StringType })
        ) { backStackEntry ->
            val siteId = backStackEntry.arguments?.getString("siteId") ?: return@composable
            BuildingSelectionScreen(
                siteId = siteId,
                onBuildingSelected = { buildingId, buildingName ->
                    NavState.crumbs.add(buildingName)
                    navController.navigate(NavRoutes.floors(buildingId))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.FLOORS,
            arguments = listOf(navArgument("buildingId") { type = NavType.StringType })
        ) { backStackEntry ->
            val buildingId = backStackEntry.arguments?.getString("buildingId") ?: return@composable
            FloorSelectionScreen(
                buildingId = buildingId,
                onFloorSelected = { floorId, floorName ->
                    NavState.crumbs.add(floorName)
                    navController.navigate(NavRoutes.campaigns(floorId))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.CAMPAIGNS,
            arguments = listOf(navArgument("floorId") { type = NavType.StringType })
        ) { backStackEntry ->
            val floorId = backStackEntry.arguments?.getString("floorId") ?: return@composable
            CampaignSelectionScreen(
                floorId = floorId,
                onCampaignSelected = { campaignId, campaignName ->
                    NavState.crumbs.add(campaignName)
                    navController.navigate(NavRoutes.cellSelection(campaignId, floorId))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.CELL_SELECTION,
            arguments = listOf(
                navArgument("campaignId") { type = NavType.StringType },
                navArgument("floorId") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val campaignId = backStackEntry.arguments?.getString("campaignId") ?: return@composable
            val floorId = backStackEntry.arguments?.getString("floorId") ?: return@composable
            CellSelectionScreen(
                campaignId = campaignId,
                floorId = floorId,
                onCellSelected = { cellId, cellLabel ->
                    NavState.crumbs.add("Cell ($cellLabel)")
                    navController.navigate(NavRoutes.capture(campaignId, floorId, cellId, cellLabel))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.CAPTURE,
            arguments = listOf(
                navArgument("campaignId") { type = NavType.StringType },
                navArgument("floorId") { type = NavType.StringType },
                navArgument("cellId") { type = NavType.StringType },
                navArgument("cellLabel") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val campaignId = backStackEntry.arguments?.getString("campaignId") ?: return@composable
            val floorId = backStackEntry.arguments?.getString("floorId") ?: return@composable
            val cellId = backStackEntry.arguments?.getString("cellId") ?: return@composable
            val cellLabel = backStackEntry.arguments?.getString("cellLabel") ?: return@composable
            CaptureScreen(
                campaignId = campaignId,
                floorId = floorId,
                cellId = cellId,
                cellLabel = cellLabel,
                onFingerprintCaptured = { fingerprintId ->
                    navController.navigate(NavRoutes.review(fingerprintId))
                },
                onBack = { navController.popBackStack() },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(
            route = NavRoutes.REVIEW,
            arguments = listOf(navArgument("fingerprintId") { type = NavType.StringType })
        ) {
            ReviewScreen(
                onDone = {
                    NavState.clear()
                    navController.navigate(NavRoutes.SYNC_STATUS) {
                        popUpTo(NavRoutes.ORGANIZATIONS)
                    }
                },
                onCaptureMore = {
                    navController.popBackStack()
                },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }

        composable(NavRoutes.SYNC_STATUS) {
            SyncStatusScreen(
                onBackToOrganizations = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                onHome = {
                    NavState.clear()
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.ORGANIZATIONS) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                breadcrumbs = NavState.crumbs.toList()
            )
        }
    }
}
