import { useEffect, useState } from 'react';
import type { ModelVersion } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate, formatStatus } from '../utils/format';
import { Toast } from '../components/Toast';

export function ModelListPage() {
  const { isOperator, isAdmin } = useAuth();
  const crud = useCrud<ModelVersion>('/models');
  const [floors, setFloors] = useState<{ id: string; name: string }[]>([]);
  const [datasets, setDatasets] = useState<{ id: string; name: string }[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [formData, setFormData] = useState({ dataset_id: '', floor_id: '', algorithm: 'knn' });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    crud.list();
    api
      .get<unknown[]>('/floors')
      .then((d) => setFloors(d as { id: string; name: string }[]))
      .catch(() => {});
    api
      .get<unknown[]>('/datasets')
      .then((d) => setDatasets(d as { id: string; name: string }[]))
      .catch(() => {});
  }, []);

  const handleTrain = async (id: string) => {
    try {
      await api.post(`/models/${id}/train`);
      setToast({ message: 'Training started', type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Train failed', type: 'error' });
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await api.patch(`/models/${id}/publish`);
      setToast({ message: 'Model published', type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Publish failed', type: 'error' });
    }
  };

  const handleCreate = async () => {
    if (!formData.dataset_id || !formData.floor_id) return;
    setSaving(true);
    try {
      await crud.create(formData);
      setFormOpen(false);
      setFormData({ dataset_id: '', floor_id: '', algorithm: 'knn' });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<ModelVersion>[] = [
    { key: 'algorithm', header: 'Algorithm', render: (r) => r.algorithm || '-' },
    { key: 'version', header: 'Version' },
    {
      key: 'status',
      header: 'Status',
      render: (r) => (
        <span className={`status-badge status-${r.status.toLowerCase()}`}>
          {formatStatus(r.status)}
        </span>
      ),
    },
    { key: 'published_at', header: 'Published', render: (r) => formatDate(r.published_at) },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: ModelVersion) => (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {r.status === 'Training' && (
                  <button
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTrain(r.id);
                    }}
                  >
                    Train
                  </button>
                )}
                {r.status === 'Ready' && (
                  <button
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePublish(r.id);
                    }}
                  >
                    Publish
                  </button>
                )}
                {isAdmin && r.status === 'Published' && (
                  <button
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      api
                        .patch(`/models/${r.id}/unpublish`)
                        .then(() => {
                          setToast({ message: 'Unpublished', type: 'success' });
                          crud.list();
                        })
                        .catch((err) => setToast({ message: err.message, type: 'error' }));
                    }}
                  >
                    Unpublish
                  </button>
                )}
                {r.status === 'Ready' && (
                  <button
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      api.patch(`/models/${r.id}/archive`).then(() => crud.list());
                    }}
                  >
                    Archive
                  </button>
                )}
                {isAdmin && (r.status === 'Training' || r.status === 'Failed') && (
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      crud.remove(r.id).then(() => crud.list());
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
        <h1>Models</h1>
        {isOperator && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setFormData({ dataset_id: '', floor_id: '', algorithm: 'knn' });
              setFormOpen(true);
            }}
          >
            Create Model
          </button>
        )}
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable columns={columns} data={crud.items.filter((m) => !m.is_deleted)} />
        </div>
      </div>
      <Modal open={formOpen} title="Create Model Version" onClose={() => setFormOpen(false)}>
        <div className="form-group">
          <label>Dataset *</label>
          <select
            value={formData.dataset_id}
            onChange={(e) => setFormData({ ...formData, dataset_id: e.target.value })}
          >
            <option value="">Select dataset...</option>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Floor *</label>
          <select
            value={formData.floor_id}
            onChange={(e) => setFormData({ ...formData, floor_id: e.target.value })}
          >
            <option value="">Select floor...</option>
            {floors.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Algorithm</label>
          <input
            value={formData.algorithm}
            onChange={(e) => setFormData({ ...formData, algorithm: e.target.value })}
          />
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={saving || !formData.dataset_id || !formData.floor_id}
          >
            {saving ? 'Creating...' : 'Create'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
