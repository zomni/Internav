import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Campaign } from '../types';
import { useCrud } from '../hooks/useCrud';
import { useAuth } from '../hooks/useAuth';
import { api } from '../services/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { SearchBox } from '../components/SearchBox';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { formatDate, formatStatus } from '../utils/format';

const STATUS_ACTIONS: Record<string, { action: string; label: string }[]> = {
  Draft: [{ action: 'start', label: 'Start (→ Ready)' }],
  Ready: [{ action: 'begin-collecting', label: 'Begin Collecting' }],
  Collecting: [
    { action: 'pause', label: 'Pause' },
    { action: 'complete', label: 'Complete' },
  ],
  Paused: [{ action: 'resume', label: 'Resume' }],
  Completed: [{ action: 'archive', label: 'Archive' }],
};

export function CampaignListPage() {
  const { isOperator, isAdmin } = useAuth();
  const navigate = useNavigate();
  const crud = useCrud<Campaign>('/campaigns');
  const [search, setSearch] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState('');
  const [formFloor, setFormFloor] = useState('');
  const [floors, setFloors] = useState<{ id: string; name: string }[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Campaign | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    crud.list();
    api
      .get<unknown[]>('/floors')
      .then((data) => setFloors(data as { id: string; name: string }[]))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!crud.items.length) return;
    let cancelled = false;
    Promise.all(
      crud.items.map(async (c) => {
        try {
          const data = await api.get<{ campaign_id: string; count: number }>(
            `/campaigns/${c.id}/fingerprints/count`,
          );
          return { id: c.id, count: data.count };
        } catch {
          return { id: c.id, count: 0 };
        }
      }),
    ).then((rows) => {
      if (cancelled) return;
      setCounts(Object.fromEntries(rows.map((r) => [r.id, r.count])));
    });
    return () => {
      cancelled = true;
    };
  }, [crud.items]);

  const filtered = crud.items.filter(
    (c) => !c.is_deleted && c.name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleAction = async (campaign: Campaign, action: string) => {
    try {
      await api.patch(`/campaigns/${campaign.id}/${action}`);
      setToast({ message: `Campaign ${action} successful`, type: 'success' });
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Action failed', type: 'error' });
    }
  };

  const handleCreate = async () => {
    if (!formName || !formFloor) return;
    setSaving(true);
    try {
      await api.post(`/floors/${formFloor}/campaigns`, { name: formName });
      setToast({ message: 'Campaign created', type: 'success' });
      setFormOpen(false);
      setFormName('');
      setFormFloor('');
      crud.list();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Create failed', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<Campaign>[] = [
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
    { key: 'started_at', header: 'Started', render: (r) => formatDate(r.started_at) },
    { key: 'finished_at', header: 'Finished', render: (r) => formatDate(r.finished_at) },
    { key: 'created_at', header: 'Created', render: (r) => formatDate(r.created_at) },
    {
      key: 'captures',
      header: 'Captures',
      render: (r) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>{counts[r.id] ?? '…'}</span>
          <button className="btn btn-sm" onClick={() => navigate(`/campaigns/${r.id}/captures`)}>
            View
          </button>
        </div>
      ),
    },
    ...(isOperator
      ? [
          {
            key: 'actions' as const,
            header: 'Actions',
            render: (r: Campaign) => (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {(STATUS_ACTIONS[r.status] || []).map((a) => (
                  <button
                    key={a.action}
                    className="btn btn-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(r, a.action);
                    }}
                  >
                    {a.label}
                  </button>
                ))}
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
      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span>{toast.message}</span>
          <button className="toast-close" onClick={() => setToast(null)}>
            &times;
          </button>
        </div>
      )}
      <div className="page-header">
        <h1>Campaigns</h1>
        {isOperator && (
          <button
            className="btn btn-primary"
            onClick={() => {
              setFormName('');
              setFormFloor('');
              setFormOpen(true);
            }}
          >
            Create Campaign
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
      <Modal open={formOpen} title="Create Campaign" onClose={() => setFormOpen(false)}>
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
        <div className="form-actions">
          <button className="btn" onClick={() => setFormOpen(false)}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={saving || !formName || !formFloor}
          >
            {saving ? 'Creating...' : 'Create'}
          </button>
        </div>
      </Modal>
      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Campaign"
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
