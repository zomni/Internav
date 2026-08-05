import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { Building, Site } from '../types';
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

export function BuildingListPage() {
  const [searchParams] = useSearchParams();
  const siteId = searchParams.get('site_id');
  const navigate = useNavigate();
  const { isOperator, isAdmin } = useAuth();
  const crud = useCrud<Building>('/buildings');
  const [site, setSite] = useState<Site | null>(null);
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Building | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Building | null>(null);
  const [formData, setFormData] = useState({ name: '', code: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      crud.list(),
      siteId
        ? api
            .get<Site>(`/sites/${siteId}`)
            .then(setSite)
            .catch(() => {})
        : Promise.resolve(),
    ]).finally(() => setLoading(false));
  }, [siteId]);

  const filtered = crud.items.filter(
    (b) =>
      !b.is_deleted &&
      (!siteId || b.site_id === siteId) &&
      (b.name.toLowerCase().includes(search.toLowerCase()) ||
        b.code.toLowerCase().includes(search.toLowerCase())),
  );

  const openCreate = () => {
    setEditing(null);
    setFormData({ name: '', code: '', description: '' });
    setFormOpen(true);
  };
  const openEdit = (b: Building) => {
    setEditing(b);
    setFormData({ name: b.name, code: b.code, description: b.description ?? '' });
    setFormOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { ...formData, site_id: siteId };
      if (editing) await crud.update(editing.id, payload);
      else await crud.create(payload);
      setFormOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<Building>[] = [
    { key: 'name', header: 'Name' },
    { key: 'code', header: 'Code' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: Building) => (
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
          { label: 'Sites', href: `/sites${site ? `?org_id=${site.organization_id}` : ''}` },
          ...(site ? [{ label: site.name }] : []),
          { label: 'Buildings' },
        ]}
      />
      <div className="page-header">
        <h1>{site ? `${site.name} — Buildings` : 'Buildings'}</h1>
        {isOperator && (
          <button className="btn btn-primary" onClick={openCreate}>
            Create Building
          </button>
        )}
      </div>
      <div className="action-bar">
        <SearchBox value={search} onChange={setSearch} />
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable
            columns={columns}
            data={filtered}
            onRowClick={(r) => navigate(`/floors?building_id=${r.id}`)}
          />
        </div>
      </div>
      <Modal
        open={formOpen}
        title={editing ? 'Edit Building' : 'Create Building'}
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
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
          />
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !formData.name || !formData.code}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </Modal>
      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Building"
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
