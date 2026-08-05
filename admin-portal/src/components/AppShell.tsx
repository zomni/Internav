import { Outlet, useLocation } from 'react-router-dom';
import { SideMenu } from './SideMenu';
import { useAuth } from '../hooks/useAuth';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/organizations': 'Organizations',
  '/sites': 'Sites',
  '/buildings': 'Buildings',
  '/floors': 'Floors',
  '/grids': 'Grids',
  '/campaigns': 'Campaigns',
  '/datasets': 'Datasets',
  '/models': 'Models',
  '/settings': 'Settings',
};

export function AppShell() {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const title = PAGE_TITLES[pathname] ?? 'IPP Admin';

  return (
    <div className="app-shell">
      <SideMenu />
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-title">{title}</div>
          <div className="topbar-user">
            {user && (
              <>
                <span className="topbar-email">{user.email}</span>
                <span className={`status-badge status-${user.role.toLowerCase()}`}>
                  {user.role}
                </span>
              </>
            )}
          </div>
        </header>
        <main className="main-content">
          <div className="container">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
