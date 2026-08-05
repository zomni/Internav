from uuid import UUID, uuid4

import pytest

from app.application.grid_service import GridService
from app.domain.entities.cell import Cell
from app.domain.entities.floor import Floor
from app.domain.entities.floor_plan import FloorPlan
from app.domain.entities.grid import Grid, GridStatus
from app.domain.errors import BusinessRuleViolation, DomainValidationError


class FakeFloorRepo:
    def __init__(self):
        self._data: dict[UUID, Floor] = {}

    def get(self, fid: UUID) -> Floor | None:
        return self._data.get(fid)

    def add(self, f: Floor) -> Floor:
        self._data[f.id] = f
        return f


class FakeFloorPlanRepo:
    def __init__(self):
        self._data: dict[UUID, FloorPlan] = {}

    def get_active(self, floor_id: UUID) -> FloorPlan | None:
        for fp in self._data.values():
            if fp.floor_id == floor_id and fp.is_active:
                return fp
        return None

    def add(self, fp: FloorPlan) -> FloorPlan:
        self._data[fp.id] = fp
        return fp


class FakeGridRepo:
    def __init__(self):
        self._data: dict[UUID, Grid] = {}

    def get(self, gid: UUID) -> Grid | None:
        return self._data.get(gid)

    def add(self, g: Grid) -> Grid:
        self._data[g.id] = g
        return g

    def update(self, g: Grid) -> Grid:
        self._data[g.id] = g
        return g

    def list_by_floor(self, floor_id: UUID) -> list[Grid]:
        return [g for g in self._data.values() if g.floor_id == floor_id]

    def has_active(self, floor_id: UUID) -> bool:
        return any(g.floor_id == floor_id and g.status == GridStatus.ACTIVE for g in self._data.values())

    def soft_delete(self, gid: UUID) -> None:
        self._data.pop(gid, None)


class FakeCellRepo:
    def __init__(self):
        self._data: dict[UUID, Cell] = {}

    def get(self, cid: UUID) -> Cell | None:
        return self._data.get(cid)

    def add(self, c: Cell) -> Cell:
        self._data[c.id] = c
        return c

    def update(self, c: Cell) -> Cell:
        self._data[c.id] = c
        return c

    def list_by_grid(self, grid_id: UUID) -> list[Cell]:
        return [c for c in self._data.values() if c.grid_id == grid_id]

    def delete_by_grid(self, grid_id: UUID) -> None:
        self._data = {k: v for k, v in self._data.items() if v.grid_id != grid_id}


class FakeCampaignRepo:
    def __init__(self):
        self._active_floors: set[UUID] = set()

    def has_active_on_floor(self, floor_id: UUID) -> bool:
        return floor_id in self._active_floors


class TestGridService:
    def setup_method(self):
        self.grid_repo = FakeGridRepo()
        self.cell_repo = FakeCellRepo()
        self.floor_repo = FakeFloorRepo()
        self.fp_repo = FakeFloorPlanRepo()
        self.campaign_repo = FakeCampaignRepo()
        self.service = GridService(
            self.grid_repo, self.cell_repo, self.floor_repo, self.fp_repo, self.campaign_repo
        )

    def _add_floor(self) -> Floor:
        f = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        self.floor_repo.add(f)
        return f

    def _add_active_floor_plan(self, floor_id: UUID) -> FloorPlan:
        fp = FloorPlan(floor_id=floor_id, image_path="/img.png", width=100, height=80, scale=0.05, checksum="abc", mime_type="image/png", is_active=True)
        self.fp_repo.add(fp)
        return fp

    def _create_grid(self, floor_id: UUID, status: GridStatus = GridStatus.DRAFT) -> Grid:
        g = Grid(floor_id=floor_id, name="Grid", cell_size=10, status=status)
        self.grid_repo.add(g)
        return g

    def test_list_by_floor_returns_empty(self):
        floor = self._add_floor()
        assert self.service.list_by_floor(floor.id) == []

    def test_list_by_floor_raises_on_missing_floor(self):
        with pytest.raises(LookupError):
            self.service.list_by_floor(uuid4())

    def test_get_returns_grid(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        result = self.service.get(g.id)
        assert result.id == g.id

    def test_get_raises_on_missing(self):
        with pytest.raises(LookupError):
            self.service.get(uuid4())

    def test_generate_creates_grid_with_cells(self):
        floor = self._add_floor()
        self._add_active_floor_plan(floor.id)
        g = self.service.generate(floor.id, "New Grid", 10)
        assert g.name == "New Grid"
        assert g.status == GridStatus.DRAFT
        cells = self.cell_repo.list_by_grid(g.id)
        # 100/10 = 10 cols, 80/10 = 8 rows = 80 cells
        assert len(cells) == 80

    def test_generate_applies_walkable_mask(self):
        floor = self._add_floor()
        self._add_active_floor_plan(floor.id)
        mask = [True] * 80
        mask[0] = False
        mask[79] = False
        g = self.service.generate(floor.id, "Masked Grid", 10, walkable_mask=mask)
        cells = self.cell_repo.list_by_grid(g.id)
        assert cells[0].walkable is False
        assert cells[79].walkable is False
        assert cells[40].walkable is True

    def test_generate_rejects_wrong_mask_length(self):
        floor = self._add_floor()
        self._add_active_floor_plan(floor.id)
        with pytest.raises(DomainValidationError, match="walkable_mask"):
            self.service.generate(floor.id, "Bad Mask", 10, walkable_mask=[True])

    def test_generate_raises_if_grid_exists(self):
        floor = self._add_floor()
        self._add_active_floor_plan(floor.id)
        self._create_grid(floor.id)
        with pytest.raises(BusinessRuleViolation, match="only one grid"):
            self.service.generate(floor.id, "Another", 10)

    def test_generate_raises_without_floor_plan(self):
        floor = self._add_floor()
        with pytest.raises(BusinessRuleViolation, match="active FloorPlan"):
            self.service.generate(floor.id, "Grid", 10)

    def test_generate_raises_on_missing_floor(self):
        with pytest.raises(LookupError):
            self.service.generate(uuid4(), "Grid", 10)

    def test_regenerate_recreates_cells(self):
        floor = self._add_floor()
        self._add_active_floor_plan(floor.id)
        g = self.service.generate(floor.id, "Grid", 10)
        self.service.regenerate(g.id)
        cells = self.cell_repo.list_by_grid(g.id)
        assert len(cells) == 80

    def test_regenerate_raises_on_locked(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.LOCKED)
        with pytest.raises(BusinessRuleViolation, match="Cannot regenerate a locked grid"):
            self.service.regenerate(g.id)

    def test_lock_sets_locked_status(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        result = self.service.lock(g.id)
        assert result.status == GridStatus.LOCKED

    def test_lock_raises_if_already_locked(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.LOCKED)
        with pytest.raises(BusinessRuleViolation, match="already locked"):
            self.service.lock(g.id)

    def test_unlock_active_to_draft(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.ACTIVE)
        result = self.service.unlock(g.id)
        assert result.status == GridStatus.DRAFT

    def test_unlock_locked_to_active(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.LOCKED)
        result = self.service.unlock(g.id)
        assert result.status == GridStatus.ACTIVE

    def test_unlock_raises_on_draft(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        with pytest.raises(BusinessRuleViolation, match="not locked"):
            self.service.unlock(g.id)

    def test_activate_sets_active(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        result = self.service.activate(g.id)
        assert result.status == GridStatus.ACTIVE

    def test_activate_raises_if_already_active(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.ACTIVE)
        with pytest.raises(BusinessRuleViolation, match="already active"):
            self.service.activate(g.id)

    def test_activate_raises_if_another_active(self):
        floor = self._add_floor()
        self._create_grid(floor.id, GridStatus.ACTIVE)
        g2 = self._create_grid(floor.id)
        with pytest.raises(BusinessRuleViolation, match="only one active grid"):
            self.service.activate(g2.id)

    def test_list_cells_returns_empty(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        assert self.service.list_cells(g.id) == []

    def test_list_cells_raises_on_missing_grid(self):
        with pytest.raises(LookupError):
            self.service.list_cells(uuid4())

    def test_update_walkable_changes_cell(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.DRAFT)
        cell = Cell(grid_id=g.id, row=0, column=0, center_x=5.0, center_y=5.0)
        self.cell_repo.add(cell)
        result = self.service.update_walkable(cell.id, False)
        assert result.walkable is False

    def test_update_walkable_allowed_on_active_grid_without_campaign(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.ACTIVE)
        cell = Cell(grid_id=g.id, row=0, column=0, center_x=5.0, center_y=5.0)
        self.cell_repo.add(cell)
        result = self.service.update_walkable(cell.id, False)
        assert result.walkable is False

    def test_update_walkable_raises_if_campaign_active(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.ACTIVE)
        self.campaign_repo._active_floors.add(floor.id)
        cell = Cell(grid_id=g.id, row=0, column=0, center_x=5.0, center_y=5.0)
        self.cell_repo.add(cell)
        with pytest.raises(BusinessRuleViolation, match="Cannot modify cells while"):
            self.service.update_walkable(cell.id, False)

    def test_update_walkable_raises_on_missing_cell(self):
        with pytest.raises(LookupError):
            self.service.update_walkable(uuid4(), False)

    def test_soft_delete_removes_grid_and_cells(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id)
        cell = Cell(grid_id=g.id, row=0, column=0, center_x=5.0, center_y=5.0)
        self.cell_repo.add(cell)
        self.service.soft_delete(g.id)
        assert self.grid_repo.get(g.id) is None
        assert self.cell_repo.get(cell.id) is None

    def test_soft_delete_raises_on_active(self):
        floor = self._add_floor()
        g = self._create_grid(floor.id, GridStatus.ACTIVE)
        with pytest.raises(BusinessRuleViolation, match="active grid"):
            self.service.soft_delete(g.id)
