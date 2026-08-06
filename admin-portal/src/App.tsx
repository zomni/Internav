import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { AppShell } from './components/AppShell';
import { LoadingOverlay } from './components/LoadingOverlay';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { OrganizationListPage } from './pages/OrganizationListPage';
import { SiteListPage } from './pages/SiteListPage';
import { BuildingListPage } from './pages/BuildingListPage';
import { FloorListPage } from './pages/FloorListPage';
import { CampaignListPage } from './pages/CampaignListPage';
import { CapturesPage } from './pages/CapturesPage';
import { DatasetListPage } from './pages/DatasetListPage';
import { GridListPage } from './pages/GridListPage';
import { GridViewPage } from './pages/GridViewPage';
import { ModelListPage } from './pages/ModelListPage';
import { SettingsPage } from './pages/SettingsPage';
import { NotFoundPage } from './pages/NotFoundPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingOverlay />;
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <LoadingOverlay />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/auth"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/organizations" element={<OrganizationListPage />} />
        <Route path="/sites" element={<SiteListPage />} />
        <Route path="/buildings" element={<BuildingListPage />} />
        <Route path="/floors" element={<FloorListPage />} />
        <Route path="/floors/:floorId/grid" element={<GridViewPage />} />
        <Route path="/campaigns" element={<CampaignListPage />} />
        <Route path="/campaigns/:campaignId/captures" element={<CapturesPage />} />
        <Route path="/datasets" element={<DatasetListPage />} />
        <Route path="/grids" element={<GridListPage />} />
        <Route path="/models" element={<ModelListPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
