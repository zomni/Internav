import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Organization } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { SearchBox } from '../components/SearchBox';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate } from '../utils/format';

export function OrganizationListPage() {
  const navigate = useNavigate();
  const { isOperator, isAdmin } = useAuth();
  const crud = useCrud<Organization>('/organizations');
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Organization | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Organization | null>(null);
  const [formData, setFormData] = useState({ name: '', code: '', description: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    crud.list();
  }, []);

  const filtered = crud.items.filter(
    (o) =>
      !o.is_deleted &&
      (o.name.toLowerCase().includes(search.toLowerCase()) ||
        o.code.toLowerCase().includes(search.toLowerCase())),
  );

  const openCreate = () => {
    setEditing(null);
    setFormData({ name: '', code: '', description: '' });
    setFormOpen(true);
  };

  const openEdit = (org: Organization) => {
    setEditing(org);
    setFormData({ name: org.name, code: org.code, description: org.description ?? '' });
    setFormOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        await crud.update(editing.id, formData);
      } else {
        await crud.create(formData);
      }
      setFormOpen(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await crud.remove(deleteTarget.id);
      setDeleteTarget(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const columns: Column<Organization>[] = [
    { key: 'name', header: 'Name' },
    { key: 'code', header: 'Code' },
    { key: 'description', header: 'Description' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: Organization) => (
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

  if (crud.loading && crud.items.length === 0) return <LoadingOverlay />;
  if (crud.error) return <ErrorView message={crud.error} onRetry={crud.list} />;

  return (
    <div>
      <div className="page-header">
        <h1>Organizations</h1>
        {isOperator && (
          <button className="btn btn-primary" onClick={openCreate}>
            Create Organization
          </button>
        )}
      </div>
      <div className="action-bar">
        <SearchBox value={search} onChange={setSearch} placeholder="Search organizations..." />
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable
            columns={columns}
            data={filtered}
            onRowClick={(r) => navigate(`/sites?org_id=${r.id}`)}
          />
        </div>
      </div>

      <Modal
        open={formOpen}
        title={editing ? 'Edit Organization' : 'Create Organization'}
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
        title="Delete Organization"
        message={`Are you sure you want to delete "${deleteTarget?.name}"?`}
        confirmLabel="Delete"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
