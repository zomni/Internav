import { useEffect, useState } from 'react';
import type { Dataset } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate, formatStatus } from '../utils/format';
import { Toast } from '../components/Toast';

export function DatasetListPage() {
  const { isOperator, isAdmin } = useAuth();
  const crud = useCrud<Dataset>('/datasets');
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Dataset | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [campaigns, setCampaigns] = useState<{ id: string; name: string; status: string }[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [addTarget, setAddTarget] = useState<Dataset | null>(null);
  const [selectedCampaigns, setSelectedCampaigns] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    crud.list();
    api
      .get<unknown[]>('/campaigns')
      .then((d) => setCampaigns(d as { id: string; name: string; status: string }[]))
      .catch(() => {});
  }, []);

  const handleBuild = async (id: string) => {
    try {
      await api.patch(`/datasets/${id}/build`);
      setToast({ message: 'Dataset built successfully', type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Build failed', type: 'error' });
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await api.patch(`/datasets/${id}/archive`);
      setToast({ message: 'Dataset archived', type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Archive failed', type: 'error' });
    }
  };

  const handleCreate = async () => {
    if (!formName) return;
    setSaving(true);
    try {
      await crud.create({ name: formName });
      setFormOpen(false);
      setFormName('');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  const handleAddCampaigns = async () => {
    if (!addTarget || selectedCampaigns.length === 0) return;
    setAdding(true);
    try {
      await api.patch(`/datasets/${addTarget.id}/add-campaigns`, {
        campaign_ids: selectedCampaigns,
      });
      setToast({ message: 'Campaigns added', type: 'success' });
      setAddOpen(false);
      setSelectedCampaigns([]);
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Add failed', type: 'error' });
    } finally {
      setAdding(false);
    }
  };

  const completedCampaigns = campaigns.filter((c) => c.status === 'Completed');

  const columns: Column<Dataset>[] = [
    { key: 'name', header: 'Name' },
    {
      key: 'status',
      header: 'Status',
      render: (r) => (
        <span className={`status-badge status-${r.status.toLowerCase()}`}>
          {formatStatus(r.status)}
        </span>
      ),
    },
    { key: 'fingerprint_count', header: 'Fingerprints' },
    { key: 'floor_count', header: 'Floors' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: Dataset) => (
              <div style={{ display: 'flex', gap: 4 }}>
                {r.status === 'Draft' && (
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      className="btn btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBuild(r.id);
                      }}
                    >
                      Build
                    </button>
                    <button
                      className="btn btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setAddTarget(r);
                        setSelectedCampaigns([]);
                        setAddOpen(true);
                      }}
                    >
                      Add Campaigns
                    </button>
                  </div>
                )}
                {(r.status === 'Ready' || r.status === 'Draft') && (
                  <button
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleArchive(r.id);
                    }}
                  >
                    Archive
                  </button>
                )}
                {isAdmin && (r.status === 'Draft' || r.status === 'Archived') && (
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
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <div className="page-header">
        <h1>Datasets</h1>
        {isOperator && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setFormName('');
              setFormOpen(true);
            }}
          >
            Create Dataset
          </button>
        )}
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable columns={columns} data={crud.items.filter((d) => !d.is_deleted)} />
        </div>
      </div>
      <Modal open={formOpen} title="Create Dataset" onClose={() => setFormOpen(false)}>
        <div className="form-group">
          <label>Name *</label>
          <input value={formName} onChange={(e) => setFormName(e.target.value)} />
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleCreate} disabled={saving || !formName}>
            {saving ? 'Creating...' : 'Create'}
          </button>
        </div>
      </Modal>
      <Modal open={addOpen} title={`Add Campaigns to "${addTarget?.name}"`} onClose={() => setAddOpen(false)}>
        {completedCampaigns.length === 0 ? (
          <p>No completed campaigns available. Complete a campaign first.</p>
        ) : (
          <div className="form-group">
            {completedCampaigns.map((c) => (
              <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={selectedCampaigns.includes(c.id)}
                  onChange={(e) =>
                    setSelectedCampaigns((prev) =>
                      e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                    )
                  }
                />
                {c.name}
              </label>
            ))}
          </div>
        )}
        <div className="form-actions">
          <button className="btn" onClick={() => setAddOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAddCampaigns}
            disabled={adding || selectedCampaigns.length === 0}
          >
            {adding ? 'Adding...' : 'Add'}
          </button>
        </div>
      </Modal>
      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Dataset"
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
