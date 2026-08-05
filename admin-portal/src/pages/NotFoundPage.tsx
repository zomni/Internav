import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div style={{ textAlign: 'center', padding: '80px 20px' }}>
      <h1 style={{ fontSize: '3rem', marginBottom: 16 }}>404</h1>
      <p style={{ color: 'var(--color-text-secondary)', marginBottom: 24 }}>Page not found</p>
      <Link to="/dashboard" className="btn btn-primary">
        Go to Dashboard
      </Link>
    </div>
  );
}
