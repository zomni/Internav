import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { Site, Organization } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { SearchBox } from '../components/SearchBox';
import { Breadcrumb } from '../components/Breadcrumb';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate } from '../utils/format';

export function SiteListPage() {
  const [searchParams] = useSearchParams();
  const orgId = searchParams.get('org_id');
  const navigate = useNavigate();
  const { isOperator, isAdmin } = useAuth();
  const crud = useCrud<Site>('/sites');
  const [org, setOrg] = useState<Organization | null>(null);
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Site | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Site | null>(null);
  const [formData, setFormData] = useState({ name: '', code: '', timezone: 'UTC', address: '' });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      crud.list(),
      orgId
        ? api
            .get<Organization>(`/organizations/${orgId}`)
            .then(setOrg)
            .catch(() => {})
        : Promise.resolve(),
    ]).finally(() => setLoading(false));
  }, [orgId]);

  const filtered = crud.items.filter(
    (s) =>
      !s.is_deleted &&
      (!orgId || s.organization_id === orgId) &&
      (s.name.toLowerCase().includes(search.toLowerCase()) ||
        s.code.toLowerCase().includes(search.toLowerCase())),
  );

  const openCreate = () => {
    setEditing(null);
    setFormData({ name: '', code: '', timezone: 'UTC', address: '' });
    setFormOpen(true);
  };

  const openEdit = (site: Site) => {
    setEditing(site);
    setFormData({
      name: site.name,
      code: site.code,
      timezone: site.timezone,
      address: site.address ?? '',
    });
    setFormOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { ...formData, organization_id: orgId };
      if (editing) {
        await crud.update(editing.id, payload);
      } else {
        await crud.create(payload);
      }
      setFormOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<Site>[] = [
    { key: 'name', header: 'Name' },
    { key: 'code', header: 'Code' },
    { key: 'timezone', header: 'Timezone' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: Site) => (
              <div style={{ display: 'flex', gap: 4 }}>
                <button
                  className="btn btn-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    openEdit(r);
                  }}
                >
                  Edit
                </button>
                {isAdmin && (
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(r);
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            ),
          },
        ]
      : []),
  ];

  if (loading && crud.items.length === 0) return <LoadingOverlay />;
  if (crud.error) return <ErrorView message={crud.error} onRetry={crud.list} />;

  return (
    <div>
      <Breadcrumb
        crumbs={[
          { label: 'Organizations', href: '/organizations' },
          ...(org ? [{ label: org.name }] : []),
          { label: 'Sites' },
        ]}
      />
      <div className="page-header">
        <h1>{org ? `${org.name} — Sites` : 'Sites'}</h1>
        {isOperator && (
          <button className="btn btn-primary" onClick={openCreate}>
            Create Site
          </button>
        )}
      </div>
      <div className="action-bar">
        <SearchBox value={search} onChange={setSearch} placeholder="Search sites..." />
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable
            columns={columns}
            data={filtered}
            onRowClick={(r) => navigate(`/buildings?site_id=${r.id}`)}
          />
        </div>
      </div>

      <Modal
        open={formOpen}
        title={editing ? 'Edit Site' : 'Create Site'}
        onClose={() => setFormOpen(false)}
      >
        <div className="form-group">
          <label>Name *</label>
          <input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Code *</label>
          <input
            value={formData.code}
            onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
          />
        </div>
        <div className="form-group">
          <label>Timezone *</label>
          <input
            value={formData.timezone}
            onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>Address</label>
          <input
            value={formData.address}
            onChange={(e) => setFormData({ ...formData, address: e.target.value })}
          />
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !formData.name || !formData.code || !formData.timezone}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </Modal>

      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Site"
        message={`Delete "${deleteTarget?.name}"?`}
        confirmLabel="Delete"
        danger
        onConfirm={() => {
          if (deleteTarget) crud.remove(deleteTarget.id).then(() => setDeleteTarget(null));
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
