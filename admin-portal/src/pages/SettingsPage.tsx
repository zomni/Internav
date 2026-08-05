import { useAuth } from '../hooks/useAuth';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
      </div>
      <div className="detail-card">
        <div className="detail-row">
          <span className="detail-label">User</span>
          <span>{user?.email}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Role</span>
          <span>{user?.role}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">API Version</span>
          <span>v1</span>
        </div>
      </div>
    </div>
  );
}
