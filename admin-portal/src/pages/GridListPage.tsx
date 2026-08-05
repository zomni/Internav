import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Grid } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate, formatStatus } from '../utils/format';
import { Toast } from '../components/Toast';

export function GridListPage() {
  const { isOperator } = useAuth();
  const navigate = useNavigate();
  const crud = useCrud<Grid>('/grids');
  const [floors, setFloors] = useState<{ id: string; name: string }[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState('');
  const [formFloor, setFormFloor] = useState('');
  const [formCellSize, setFormCellSize] = useState(1);
  const [analyze, setAnalyze] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    crud.list();
    api
      .get<unknown[]>('/floors')
      .then((data) => setFloors(data as { id: string; name: string }[]))
      .catch(() => {});
  }, []);

  const handleAction = async (id: string, action: string) => {
    try {
      await api.post(`/grids/${id}/${action}`);
      setToast({ message: `Grid ${action} successful`, type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Action failed', type: 'error' });
    }
  };

  const handleCreate = async () => {
    if (!formName || !formFloor) return;
    setSaving(true);
    try {
      await api.post(`/floors/${formFloor}/grids`, {
        name: formName,
        cell_size: formCellSize,
        analyze_walkability: analyze,
      });
      setFormOpen(false);
      setFormName('');
      setFormFloor('');
      setFormCellSize(1);
      setAnalyze(false);
      crud.list();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<Grid>[] = [
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
    { key: 'cell_size', header: 'Cell Size' },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    {
      key: 'actions' as const,
      header: 'Actions',
      render: (r: Grid) => (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          <button
            className="btn btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/floors/${r.floor_id}/grid`);
            }}
          >
            View
          </button>
          {isOperator && r.status === 'Draft' && (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleAction(r.id, 'activate');
              }}
            >
              Activate
            </button>
          )}
          {isOperator && r.status === 'Active' && (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleAction(r.id, 'lock');
              }}
            >
              Lock
            </button>
          )}
          {isOperator && r.status === 'Locked' && (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleAction(r.id, 'unlock');
              }}
            >
              Unlock
            </button>
          )}
          {isOperator && (r.status === 'Active' || r.status === 'Locked') && (
            <button
              className="btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleAction(r.id, 'regenerate');
              }}
            >
              Regenerate
            </button>
          )}
        </div>
      ),
    },
  ];

  if (crud.loading && crud.items.length === 0) return <LoadingOverlay />;
  if (crud.error) return <ErrorView message={crud.error} onRetry={crud.list} />;

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <div className="page-header">
        <h1>Grids</h1>
        {isOperator && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setFormName('');
              setFormFloor('');
              setFormCellSize(1);
              setAnalyze(false);
              setFormOpen(true);
            }}
          >
            Generate Grid
          </button>
        )}
      </div>
      <div className="card">
        <div className="card-body">
          <DataTable columns={columns} data={crud.items.filter((g) => !g.is_deleted)} />
        </div>
      </div>

      <Modal open={formOpen} title="Generate Grid" onClose={() => setFormOpen(false)}>
        <div className="form-group">
          <label>Name *</label>
          <input value={formName} onChange={(e) => setFormName(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Floor *</label>
          <select value={formFloor} onChange={(e) => setFormFloor(e.target.value)}>
            <option value="">Select floor...</option>
            {floors.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Cell Size *</label>
          <input
            type="number"
            min={0.1}
            step={0.1}
            value={formCellSize}
            onChange={(e) => setFormCellSize(Number(e.target.value))}
          />
        </div>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={analyze}
              onChange={(e) => setAnalyze(e.target.checked)}
            />{' '}
            Analyze walkability from floor plan
          </label>
        </div>
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={saving || !formName || !formFloor}
          >
            {saving ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
