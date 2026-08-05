package com.internav.user.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.internav.user.ui.screens.*
import com.internav.user.util.Prefs

@Composable
fun UserNavGraph(navController: NavHostController) {
    NavHost(navController = navController, startDestination = NavRoutes.LOGIN) {

        composable(NavRoutes.LOGIN) {
            val context = LocalContext.current
            LoginScreen(onLoginSuccess = {
                val buildingId = Prefs.lastBuildingId(context)
                if (buildingId != null) {
                    navController.navigate(NavRoutes.map(buildingId)) {
                        popUpTo(NavRoutes.LOGIN) { inclusive = true }
                    }
                } else {
                    navController.navigate(NavRoutes.ORGANIZATIONS) {
                        popUpTo(NavRoutes.LOGIN) { inclusive = true }
                    }
                }
            })
        }

        composable(NavRoutes.ORGANIZATIONS) {
            OrganizationSelectionScreen(onOrgSelected = { orgId ->
                navController.navigate(NavRoutes.sites(orgId))
            })
        }

        composable(
            route = NavRoutes.SITES,
            arguments = listOf(navArgument("orgId") { type = NavType.StringType })
        ) {
            val orgId = it.arguments?.getString("orgId") ?: return@composable
            SiteSelectionScreen(organizationId = orgId, onSiteSelected = { siteId ->
                navController.navigate(NavRoutes.buildings(siteId))
            })
        }

        composable(
            route = NavRoutes.BUILDINGS,
            arguments = listOf(navArgument("siteId") { type = NavType.StringType })
        ) {
            val siteId = it.arguments?.getString("siteId") ?: return@composable
            BuildingSelectionScreen(siteId = siteId, onBuildingSelected = { buildingId ->
                navController.navigate(NavRoutes.map(buildingId))
            })
        }

        composable(
            route = NavRoutes.MAP,
            arguments = listOf(navArgument("buildingId") { type = NavType.StringType })
        ) {
            val buildingId = it.arguments?.getString("buildingId") ?: return@composable
            MapScreen(buildingId = buildingId, onBack = { navController.popBackStack() })
        }
    }
}
