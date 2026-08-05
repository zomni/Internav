import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { Floor, Building } from '../types';
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

export function FloorListPage() {
  const [searchParams] = useSearchParams();
  const buildingId = searchParams.get('building_id');
  const { isOperator, isAdmin } = useAuth();
  const navigate = useNavigate();
  const crud = useCrud<Floor>('/floors');
  const [building, setBuilding] = useState<Building | null>(null);
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Floor | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Floor | null>(null);
  const [formData, setFormData] = useState({ name: '', level: 0, display_order: 0 });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      crud.list(),
      buildingId
        ? api
            .get<Building>(`/buildings/${buildingId}`)
            .then(setBuilding)
            .catch(() => {})
        : Promise.resolve(),
    ]).finally(() => setLoading(false));
  }, [buildingId]);

  const filtered = crud.items.filter(
    (f) =>
      !f.is_deleted &&
      (!buildingId || f.building_id === buildingId) &&
      f.name.toLowerCase().includes(search.toLowerCase()),
  );

  const openCreate = () => {
    setEditing(null);
    setFormData({ name: '', level: 0, display_order: 0 });
    setFormOpen(true);
  };
  const openEdit = (f: Floor) => {
    setEditing(f);
    setFormData({ name: f.name, level: f.level, display_order: f.display_order });
    setFormOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { ...formData, building_id: buildingId };
      if (editing) await crud.update(editing.id, payload);
      else await crud.create(payload);
      setFormOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<Floor>[] = [
    { key: 'name', header: 'Name' },
    { key: 'level', header: 'Level' },
    { key: 'display_order', header: 'Order' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    {
      key: 'actions' as const,
      header: 'Actions',
      render: (r: Floor) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            className="btn btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/floors/${r.id}/grid`);
            }}
          >
            View
          </button>
          {isOperator && (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                openEdit(r);
              }}
            >
              Edit
            </button>
          )}
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
  ];

  if (loading && crud.items.length === 0) return <LoadingOverlay />;
  if (crud.error) return <ErrorView message={crud.error} onRetry={crud.list} />;

  return (
    <div>
      <Breadcrumb
        crumbs={[
          { label: 'Organizations', href: '/organizations' },
          { label: 'Sites', href: `/sites` },
          {
            label: 'Buildings',
            href: `/buildings${building ? `?site_id=${building.site_id}` : ''}`,
          },
          ...(building ? [{ label: building.name }] : []),
          { label: 'Floors' },
        ]}
      />
      <div className="page-header">
        <h1>{building ? `${building.name} — Floors` : 'Floors'}</h1>
        {isOperator && (
          <button className="btn btn-primary" onClick={openCreate}>
            Create Floor
          </button>
        )}
      </div>
      <div className="action-bar">
        <SearchBox value={search} onChange={setSearch} />
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable columns={columns} data={filtered} />
        </div>
      </div>
      <Modal
        open={formOpen}
        title={editing ? 'Edit Floor' : 'Create Floor'}
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
          <label>Level</label>
          <input
            type="number"
            value={formData.level}
            onChange={(e) => setFormData({ ...formData, level: Number(e.target.value) })}
          />
        </div>
        <div className="form-group">
          <label>Display Order</label>
          <input
            type="number"
            value={formData.display_order}
            onChange={(e) => setFormData({ ...formData, display_order: Number(e.target.value) })}
          />
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || !formData.name}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </Modal>
      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Floor"
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
