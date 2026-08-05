import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Building, Cell, Floor, FloorPlan, Grid } from '../types';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Breadcrumb } from '../components/Breadcrumb';
import { LoadingOverlay } from '../components/LoadingOverlay';
import { ErrorView } from '../components/ErrorView';
import { Toast } from '../components/Toast';
import { formatStatus } from '../utils/format';

const PLAN_IMAGE_URL = (planId: string) => `/api/v1/floor-plans/${planId}/image`;

export function GridViewPage() {
  const { floorId = '' } = useParams();
  const navigate = useNavigate();
  const { isOperator } = useAuth();
  const [floor, setFloor] = useState<Floor | null>(null);
  const [building, setBuilding] = useState<Building | null>(null);
  const [plan, setPlan] = useState<FloorPlan | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [jump, setJump] = useState('');
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const markerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const floorData = await api.get<Floor>(`/floors/${floorId}`);
        if (cancelled) return;
        setFloor(floorData);
        const buildingData = await api
          .get<Building>(`/buildings/${floorData.building_id}`)
          .catch(() => null);
        if (cancelled) return;
        setBuilding(buildingData);

        const plans = await api.get<FloorPlan[]>(`/floors/${floorId}/floor-plans`);
        const activePlan = plans.find((p) => p.is_active) ?? plans[0] ?? null;
        if (cancelled) return;
        setPlan(activePlan);

        const grids = await api.get<Grid[]>(`/floors/${floorId}/grids`);
        const activeGrid = grids.find((g) => g.status === 'Active') ?? grids[0] ?? null;
        if (cancelled) return;
        setGrid(activeGrid);
        if (activeGrid) {
          const cellData = await api.get<Cell[]>(`/grids/${activeGrid.id}/cells`);
          if (cancelled) return;
          setCells(cellData);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load grid');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [floorId]);

  const walkableCount = useMemo(() => cells.filter((c) => c.walkable).length, [cells]);

  const nCols = useMemo(() => {
    if (cells.length === 0) return 0;
    return Math.max(...cells.map((c) => c.column)) + 1;
  }, [cells]);

  const cellNumber = (cell: Cell) => (nCols > 0 ? cell.row * nCols + cell.column + 1 : 0);

  const handleToggle = async (cell: Cell) => {
    if (!isOperator || savingId) return;
    setSavingId(cell.id);
    try {
      const updated = await api.put<Cell>(`/cells/${cell.id}/walkable`, {
        walkable: !cell.walkable,
      });
      setCells((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setToast({
        message: `Cell #${cellNumber(cell)} (${updated.row},${updated.column}) marked ${updated.walkable ? 'walkable' : 'blocked'}`,
        type: 'success',
      });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Update failed', type: 'error' });
    } finally {
      setSavingId(null);
    }
  };

  const jumpToCell = (raw: string) => {
    const n = parseInt(raw.replace('#', '').trim(), 10);
    if (Number.isNaN(n) || n < 1) {
      setHighlightId(null);
      return;
    }
    const target = cells.find((c) => cellNumber(c) === n);
    if (!target) {
      setToast({
        message: `Cell #${n} not found (grid has 1..${cells.length})`,
        type: 'error',
      });
      setHighlightId(null);
      return;
    }
    setHighlightId(target.id);
    requestAnimationFrame(() => {
      markerRef.current?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
    });
  };

  if (loading && !grid) return <LoadingOverlay />;
  if (error) return <ErrorView message={error} onRetry={() => window.location.reload()} />;

  const cellSize = grid?.cell_size ?? 1;

  const highlightCell = highlightId ? (cells.find((c) => c.id === highlightId) ?? null) : null;

  return (
    <div>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <Breadcrumb
        crumbs={[
          { label: 'Organizations', href: '/organizations' },
          { label: 'Sites', href: '/sites' },
          { label: 'Buildings', href: '/buildings' },
          {
            label: building ? `${building.name} — Floors` : 'Floors',
            href: `/floors${building ? `?building_id=${building.id}` : ''}`,
          },
          { label: floor ? floor.name : 'Floor' },
        ]}
      />
      <div className="page-header">
        <div>
          <h1>{grid ? grid.name : 'Grid View'}</h1>
          {floor && (
            <p className="page-subtitle">
              Floor {floor.name}
              {building ? ` · ${building.name}` : ''}
            </p>
          )}
        </div>
        <button
          className="btn"
          onClick={() => navigate(`/floors${building ? `?building_id=${building.id}` : ''}`)}
        >
          Back to Floors
        </button>
      </div>

      {!plan && (
        <div className="card">
          <div className="card-body">
            <p>No active floor plan for this floor. Upload a floor plan first.</p>
          </div>
        </div>
      )}

      {!grid && (
        <div className="card">
          <div className="card-body">
            <p>No grid for this floor. Generate a grid first.</p>
          </div>
        </div>
      )}

      {grid && plan && (
        <div className="card">
          <div className="card-header">
            <div className="grid-meta">
              <span className={`status-badge status-${grid.status.toLowerCase()}`}>
                {formatStatus(grid.status)}
              </span>
              <span className="grid-meta-item">
                Cell size: <strong>{grid.cell_size}px</strong>
              </span>
              <span className="grid-meta-item">
                Plan: <strong>v{plan.version}</strong>
              </span>
              <span className="grid-meta-item">
                Cells: <strong>{cells.length}</strong>
              </span>
              <span className="grid-meta-item">
                Walkable: <strong>{walkableCount}</strong> / {cells.length}
              </span>
            </div>
            <div className="grid-toolbar">
              <div className="cell-search">
                <input
                  value={jump}
                  onChange={(e) => setJump(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') jumpToCell(jump);
                  }}
                  placeholder="Jump to cell #"
                  inputMode="numeric"
                />
                <button className="btn btn-sm btn-primary" onClick={() => jumpToCell(jump)}>
                  Go
                </button>
              </div>
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
            <div className="legend">
              <span className="legend-item">
                <span className="legend-swatch walkable" /> Walkable
              </span>
              <span className="legend-item">
                <span className="legend-swatch blocked" /> Blocked
              </span>
              {highlightCell && (
                <span className="legend-item legend-note">
                  Cell #{cellNumber(highlightCell)} highlighted
                </span>
              )}
              {isOperator && (
                <span className="legend-item legend-note">Click a cell to toggle walkability</span>
              )}
            </div>

            {viewMode === 'map' ? (
              <div className="grid-container">
                <img src={PLAN_IMAGE_URL(plan.id)} alt={`Floor plan v${plan.version}`} />
                <svg viewBox={`0 0 ${plan.width} ${plan.height}`} className="grid-overlay">
                  {cells.map((cell) => (
                    <g
                      key={cell.id}
                      onClick={() => handleToggle(cell)}
                      className={`grid-cell${cell.id === highlightId ? ' is-highlight' : ''}${isOperator && !savingId ? ' is-editable' : ''}`}
                      opacity={savingId === cell.id ? 0.4 : 1}
                    >
                      <rect
                        x={cell.column * cellSize}
                        y={cell.row * cellSize}
                        width={cellSize}
                        height={cellSize}
                        fill={cell.walkable ? 'rgba(22,163,74,0.30)' : 'rgba(148,163,184,0.42)'}
                        stroke="rgba(15,23,42,0.14)"
                        strokeWidth={1}
                      >
                        <title>{`#${cellNumber(cell)} (${cell.row},${cell.column}) ${cell.walkable ? 'walkable' : 'blocked'}`}</title>
                      </rect>
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
                  ))}
                </svg>
                {highlightCell && (
                  <div
                    ref={markerRef}
                    style={{
                      position: 'absolute',
                      left: `${((highlightCell.column + 0.5) * cellSize * 100) / plan.width}%`,
                      top: `${((highlightCell.row + 0.5) * cellSize * 100) / plan.height}%`,
                      width: 1,
                      height: 1,
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Row</th>
                      <th>Column</th>
                      <th>Center</th>
                      <th>Status</th>
                      {isOperator && <th>Action</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {cells.map((cell) => (
                      <tr
                        key={cell.id}
                        className={cell.id === highlightId ? 'is-highlight-row' : ''}
                      >
                        <td>
                          <span className="cell-number">#{cellNumber(cell)}</span>
                        </td>
                        <td>{cell.row}</td>
                        <td>{cell.column}</td>
                        <td>
                          {cell.center_x.toFixed(1)}, {cell.center_y.toFixed(1)}
                        </td>
                        <td>
                          <span
                            className={`status-badge status-${cell.walkable ? 'active' : 'inactive'}`}
                          >
                            {cell.walkable ? 'Walkable' : 'Blocked'}
                          </span>
                        </td>
                        {isOperator && (
                          <td>
                            <button
                              className="btn btn-sm"
                              onClick={() => handleToggle(cell)}
                              disabled={savingId === cell.id}
                            >
                              {savingId === cell.id
                                ? 'Saving...'
                                : cell.walkable
                                  ? 'Block'
                                  : 'Unblock'}
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
