import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';

export function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<unknown[]>('/organizations'),
      api.get<unknown[]>('/sites'),
      api.get<unknown[]>('/buildings'),
      api.get<unknown[]>('/floors'),
      api.get<unknown[]>('/campaigns' + '?page_size=1'),
      api.get<unknown[]>('/datasets'),
      api.get<unknown[]>('/models'),
      api.get<unknown[]>('/users'),
    ])
      .then(([orgs, sites, buildings, floors, camps, datasets, models, users]) => {
        setStats({
          Organizations: Array.isArray(orgs) ? orgs.length : 0,
          Sites: Array.isArray(sites) ? sites.length : 0,
          Buildings: Array.isArray(buildings) ? buildings.length : 0,
          Floors: Array.isArray(floors) ? floors.length : 0,
          Campaigns: Array.isArray(camps) ? (camps as { total?: number }[]).length : 0,
          Datasets: Array.isArray(datasets) ? datasets.length : 0,
          Models: Array.isArray(models) ? models.length : 0,
          Users: Array.isArray(users) ? users.length : 0,
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load stats'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay />;
  if (error) return <ErrorView message={error} onRetry={() => window.location.reload()} />;

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 24 }}>
        Welcome, {user?.email}
      </p>
      <div className="stats-grid">
        {stats &&
          Object.entries(stats).map(([label, value]) => (
            <div key={label} className="stat-card">
              <h3>{label}</h3>
              <div className="stat-value">{value}</div>
            </div>
          ))}
      </div>
    </div>
  );
}
