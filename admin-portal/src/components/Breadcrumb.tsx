import { Link } from 'react-router-dom';

interface Crumb {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  crumbs: Crumb[];
}

export function Breadcrumb({ crumbs }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb">
      {crumbs.map((c, i) => (
        <span key={i}>
          {c.href ? (
            <Link to={c.href}>{c.label}</Link>
          ) : (
            <span className="breadcrumb-current">{c.label}</span>
          )}
          {i < crumbs.length - 1 && <span className="breadcrumb-sep">/</span>}
        </span>
      ))}
    </nav>
  );
}
