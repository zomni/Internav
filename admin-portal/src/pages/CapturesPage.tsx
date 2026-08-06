import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Building, Campaign, Cell, Fingerprint, Floor, FloorPlan, Grid } from '../types';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Breadcrumb } from '../components/Breadcrumb';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { Toast } from '../components/Toast';
import { Modal } from '../components/Modal';
import { ConfirmationDialog } from '../components/ConfirmationDialog';
import { formatDate } from '../utils/format';

const PLAN_IMAGE_URL = (planId: string) => `/api/v1/floor-plans/${planId}/image`;

function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t;
}

function cellCaptureColor(count: number): string {
  if (count <= 0) return 'rgba(220,38,38,0.55)';
  if (count >= 10) return 'rgba(22,163,74,0.55)';
  const t = count / 10;
  const r = Math.round(lerp(0xdc, 0x16, t));
  const g = Math.round(lerp(0x26, 0xa3, t));
  const b = Math.round(lerp(0x26, 0x4a, t));
  return `rgba(${r},${g},${b},0.55)`;
}

const LOCKED_STATUSES = ['Completed', 'Archived'];

export function CapturesPage() {
  const { campaignId = '' } = useParams();
  const navigate = useNavigate();
  const { isOperator } = useAuth();

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [floor, setFloor] = useState<Floor | null>(null);
  const [building, setBuilding] = useState<Building | null>(null);
  const [plan, setPlan] = useState<FloorPlan | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [fingerprints, setFingerprints] = useState<Fingerprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [selectedCell, setSelectedCell] = useState<Cell | null>(null);
  const [viewFingerprint, setViewFingerprint] = useState<Fingerprint | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Fingerprint | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const canDelete = isOperator && campaign !== null && !LOCKED_STATUSES.includes(campaign.status);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const campaignData = await api.get<Campaign>(`/campaigns/${campaignId}`);
      setCampaign(campaignData);
      const floorData = await api.get<Floor>(`/floors/${campaignData.floor_id}`);
      setFloor(floorData);
      const buildingData = await api
        .get<Building>(`/buildings/${floorData.building_id}`)
        .catch(() => null);
      setBuilding(buildingData);

      const plans = await api.get<FloorPlan[]>(`/floors/${floorData.id}/floor-plans`);
      const activePlan = plans.find((p) => p.is_active) ?? plans[0] ?? null;
      setPlan(activePlan);

      const grids = await api.get<Grid[]>(`/floors/${floorData.id}/grids`);
      const activeGrid = grids.find((g) => g.status === 'Active') ?? grids[0] ?? null;
      setGrid(activeGrid);
      if (activeGrid) {
        const cellData = await api.get<Cell[]>(`/grids/${activeGrid.id}/cells`);
        setCells(cellData);
      }

      const fpData = await api.get<Fingerprint[]>(`/campaigns/${campaignData.id}/fingerprints`);
      setFingerprints(fpData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load captures');
    } finally {
      setLoading(false);
    }
  }, [campaignId]);

  useEffect(() => {
    load();
  }, [load]);

  const nCols = useMemo(() => {
    if (cells.length === 0) return 0;
    return Math.max(...cells.map((c) => c.column)) + 1;
  }, [cells]);

  const cellNumber = (cell: Cell) => (nCols > 0 ? cell.row * nCols + cell.column + 1 : 0);

  const cellById = useMemo(() => new Map(cells.map((c) => [c.id, c])), [cells]);

  const countsByCell = useMemo(() => {
    const counts = new Map<string, number>();
    for (const fp of fingerprints) {
      counts.set(fp.cell_id, (counts.get(fp.cell_id) ?? 0) + 1);
    }
    return counts;
  }, [fingerprints]);

  const filtered = useMemo(() => {
    const list = selectedCell
      ? fingerprints.filter((fp) => fp.cell_id === selectedCell.id)
      : fingerprints;
    return [...list].sort(
      (a, b) => a.sample_number - b.sample_number || a.captured_at.localeCompare(b.captured_at),
    );
  }, [fingerprints, selectedCell]);

  const openView = async (fp: Fingerprint) => {
    try {
      const detail = await api.get<Fingerprint>(`/fingerprints/${fp.id}`);
      setViewFingerprint(detail);
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Failed to load details',
        type: 'error',
      });
    }
  };

  const handleDelete = async () => {
    const target = deleteTarget;
    setDeleteTarget(null);
    if (!target) return;
    try {
      await api.delete(`/fingerprints/${target.id}`);
      setToast({ message: `Capture from ${target.device_id} deleted`, type: 'success' });
      await load();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Delete failed', type: 'error' });
    }
  };

  if (loading && !campaign) return <LoadingOverlay />;
  if (error) return <ErrorView message={error} onRetry={load} />;

  const cellSize = grid?.cell_size ?? 1;

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <Breadcrumb
        crumbs={[
          { label: 'Campaigns', href: '/campaigns' },
          { label: campaign ? campaign.name : 'Campaign' },
          { label: 'Captures' },
        ]}
      />
      <div className="page-header">
        <div>
          <h1>Captures</h1>
          {campaign && (
            <p className="page-subtitle">
              {campaign.name}
              {floor ? ` · Floor ${floor.name}` : ''}
              {building ? ` · ${building.name}` : ''}
            </p>
          )}
        </div>
        <button className="btn" onClick={() => navigate('/campaigns')}>
          Back to Campaigns
        </button>
      </div>

      {!campaign ? null : (
        <div className="card">
          <div className="card-header">
            <div className="grid-meta">
              <span className={`status-badge status-${campaign.status.toLowerCase()}`}>
                {campaign.status}
              </span>
              <span className="grid-meta-item">
                Captures: <strong>{fingerprints.length}</strong>
              </span>
              <span className="grid-meta-item">
                Cells with data: <strong>{countsByCell.size}</strong>
              </span>
              {selectedCell && (
                <span className="grid-meta-item">
                  Filtered:{' '}
                  <strong>
                    #{cellNumber(selectedCell)} ({selectedCell.row},{selectedCell.column})
                  </strong>
                </span>
              )}
            </div>
            <div className="grid-toolbar">
              <div className="view-toggle">
                <button
                  className={`view-toggle-btn${viewMode === 'map' ? ' active' : ''}`}
                  onClick={() => setViewMode('map')}
                >
                  Map
                </button>
                <button
                  className={`view-toggle-btn${viewMode === 'list' ? ' active' : ''}`}
                  onClick={() => setViewMode('list')}
                >
                  List
                </button>
              </div>
            </div>
          </div>
          <div className="card-body">
            {!plan && <p>No active floor plan for this floor. Upload a floor plan first.</p>}
            {!grid && <p>No grid for this floor. Generate a grid first.</p>}

            {grid && plan && (
              <div className="legend">
                <span className="legend-item">
                  <span className="legend-swatch walkable" /> Captures 0
                </span>
                <span className="legend-item">
                  <span className="legend-swatch active" /> Captures ≥ 10
                </span>
                {isOperator && (
                  <span className="legend-item legend-note">Click a cell to filter captures</span>
                )}
              </div>
            )}

            {viewMode === 'map' && grid && plan ? (
              <div className="grid-container">
                <img src={PLAN_IMAGE_URL(plan.id)} alt={`Floor plan v${plan.version}`} />
                <svg viewBox={`0 0 ${plan.width} ${plan.height}`} className="grid-overlay">
                  {cells.map((cell) => {
                    const count = countsByCell.get(cell.id) ?? 0;
                    const isSelected = selectedCell?.id === cell.id;
                    return (
                      <g
                        key={cell.id}
                        onClick={() => setSelectedCell(isSelected ? null : cell)}
                        className={`grid-cell${isSelected ? ' is-highlight' : ''}${isOperator ? ' is-editable' : ''}`}
                      >
                        <rect
                          x={cell.column * cellSize}
                          y={cell.row * cellSize}
                          width={cellSize}
                          height={cellSize}
                          fill={cell.walkable ? cellCaptureColor(count) : 'rgba(148,163,184,0.42)'}
                          stroke="rgba(15,23,42,0.14)"
                          strokeWidth={1}
                        >
                          <title>{`#${cellNumber(cell)} (${cell.row},${cell.column}) · ${count} capture${count === 1 ? '' : 's'}`}</title>
                        </rect>
                        {cell.walkable && count > 0 && cellSize >= 24 && (
                          <g>
                            <circle
                              cx={(cell.column + 0.92) * cellSize}
                              cy={(cell.row + 0.08) * cellSize}
                              r={Math.max(6, cellSize * 0.18)}
                              fill="rgba(15,23,42,0.85)"
                              stroke="rgba(255,255,255,0.9)"
                              strokeWidth={1}
                              style={{ pointerEvents: 'none' }}
                            />
                            <text
                              x={(cell.column + 0.92) * cellSize}
                              y={(cell.row + 0.08) * cellSize}
                              textAnchor="middle"
                              dominantBaseline="central"
                              fontSize={Math.max(7, cellSize * 0.2)}
                              fill="#fff"
                              style={{ pointerEvents: 'none' }}
                            >
                              {count}
                            </text>
                          </g>
                        )}
                        {cellSize >= 40 && (
                          <text
                            x={(cell.column + 0.5) * cellSize}
                            y={(cell.row + 0.5) * cellSize}
                            textAnchor="middle"
                            dominantBaseline="central"
                            fontSize={Math.max(8, cellSize * 0.26)}
                            fill="rgba(15,23,42,0.72)"
                            stroke="rgba(255,255,255,0.9)"
                            strokeWidth={2}
                            paintOrder="stroke"
                            style={{ pointerEvents: 'none' }}
                          >
                            {cellNumber(cell)}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </svg>
              </div>
            ) : (
              <div className="table-wrapper">
                {filtered.length === 0 ? (
                  <div className="table-empty">No captures found.</div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Cell</th>
                        <th>Sample #</th>
                        <th>Device</th>
                        <th>Captured</th>
                        <th>Observations</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((fp) => {
                        const cell = cellById.get(fp.cell_id);
                        return (
                          <tr key={fp.id}>
                            <td>
                              <span className="cell-number">
                                {cell ? `#${cellNumber(cell)} (${cell.row},${cell.column})` : '-'}
                              </span>
                            </td>
                            <td>{fp.sample_number}</td>
                            <td>{fp.device_id}</td>
                            <td>{formatDate(fp.captured_at)}</td>
                            <td>{fp.observations.length}</td>
                            <td>
                              <div style={{ display: 'flex', gap: 4 }}>
                                <button className="btn btn-sm" onClick={() => openView(fp)}>
                                  View
                                </button>
                                {canDelete && (
                                  <button
                                    className="btn btn-sm btn-danger"
                                    onClick={() => setDeleteTarget(fp)}
                                  >
                                    Delete
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <Modal
        open={!!viewFingerprint}
        title={
          viewFingerprint
            ? `Capture #${viewFingerprint.sample_number} · ${viewFingerprint.device_id}`
            : 'Capture'
        }
        onClose={() => setViewFingerprint(null)}
      >
        {viewFingerprint && (
          <div>
            <p>
              <strong>Cell:</strong>{' '}
              {viewFingerprint.cell_id
                ? (() => {
                    const cell = cellById.get(viewFingerprint.cell_id);
                    return cell
                      ? `#${cellNumber(cell)} (${cell.row},${cell.column})`
                      : viewFingerprint.cell_id;
                  })()
                : '-'}{' '}
              · <strong>Captured:</strong> {formatDate(viewFingerprint.captured_at)} ·{' '}
              <strong>Orientation:</strong> {viewFingerprint.orientation}
            </p>
            {viewFingerprint.notes && (
              <p>
                <strong>Notes:</strong> {viewFingerprint.notes}
              </p>
            )}
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>BSSID</th>
                    <th>SSID</th>
                    <th>RSSI</th>
                    <th>Frequency</th>
                    <th>Channel</th>
                    <th>Band</th>
                    <th>Security</th>
                  </tr>
                </thead>
                <tbody>
                  {viewFingerprint.observations.length === 0 && (
                    <tr>
                      <td colSpan={7} className="table-empty">
                        No observations.
                      </td>
                    </tr>
                  )}
                  {viewFingerprint.observations.map((obs) => (
                    <tr key={obs.id}>
                      <td className="cell-number">{obs.bssid}</td>
                      <td>{obs.ssid || '-'}</td>
                      <td>{obs.rssi}</td>
                      <td>{obs.frequency}</td>
                      <td>{obs.channel || '-'}</td>
                      <td>{obs.band || '-'}</td>
                      <td>{obs.security || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Modal>

      <ConfirmationDialog
        open={!!deleteTarget}
        title="Delete Capture"
        message={`Delete capture #${deleteTarget?.sample_number} from ${deleteTarget?.device_id}?`}
        confirmLabel="Delete"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
