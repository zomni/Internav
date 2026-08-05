import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const menuSections = [
  {
    label: 'Overview',
    items: [{ path: '/dashboard', label: 'Dashboard', icon: '📊' }],
  },
  {
    label: 'Management',
    items: [
      { path: '/organizations', label: 'Organizations', icon: '🏢' },
      { path: '/sites', label: 'Sites', icon: '📍' },
      { path: '/buildings', label: 'Buildings', icon: '🏛️' },
      { path: '/floors', label: 'Floors', icon: '🏗️' },
      { path: '/grids', label: 'Grids', icon: '📐' },
    ],
  },
  {
    label: 'Data',
    items: [
      { path: '/campaigns', label: 'Campaigns', icon: '📋' },
      { path: '/datasets', label: 'Datasets', icon: '💾' },
      { path: '/models', label: 'Models', icon: '🧠' },
    ],
  },
  {
    label: 'System',
    items: [{ path: '/settings', label: 'Settings', icon: '⚙️' }],
  },
];

export function SideMenu() {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">IP</span>
        IPP Admin
      </div>
      <nav className="sidebar-nav">
        {menuSections.map((section) => (
          <div key={section.label}>
            <div className="sidebar-section-title">{section.label}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
              >
                <span className="sidebar-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">{user?.email}</div>
        <button className="sidebar-logout" onClick={logout}>
          Logout
        </button>
      </div>
    </aside>
  );
}
