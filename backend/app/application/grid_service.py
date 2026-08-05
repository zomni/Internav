import math
from uuid import UUID

from app.domain.entities.cell import Cell
from app.domain.entities.grid import Grid, GridStatus
from app.domain.errors import BusinessRuleViolation, DomainValidationError
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cell_repository import CellRepository
from app.repositories.floor_plan_repository import FloorPlanRepository
from app.repositories.floor_repository import FloorRepository
from app.repositories.grid_repository import GridRepository


class GridService:
    def __init__(
        self,
        grid_repository: GridRepository,
        cell_repository: CellRepository,
        floor_repository: FloorRepository,
        floor_plan_repository: FloorPlanRepository,
        campaign_repository: CampaignRepository,
    ) -> None:
        self._grid_repo = grid_repository
        self._cell_repo = cell_repository
        self._floor_repo = floor_repository
        self._floor_plan_repo = floor_plan_repository
        self._campaign_repo = campaign_repository

    def list_all(self) -> list[Grid]:
        return self._grid_repo.list_all()

    def list_by_floor(self, floor_id: UUID) -> list[Grid]:
        self._require_floor(floor_id)
        return self._grid_repo.list_by_floor(floor_id)

    def get(self, grid_id: UUID) -> Grid:
        grid = self._grid_repo.get(grid_id)
        if grid is None:
            raise LookupError("Grid not found.")
        return grid

    def generate(
        self,
        floor_id: UUID,
        name: str,
        cell_size: int,
        walkable_mask: list[bool] | None = None,
    ) -> Grid:
        self._require_floor(floor_id)

        if self._grid_repo.list_by_floor(floor_id):
            raise BusinessRuleViolation(
                "A floor can have only one grid. Delete the existing grid first."
            )

        fp = self._floor_plan_repo.get_active(floor_id)
        if fp is None:
            raise BusinessRuleViolation("An active FloorPlan is required to generate a grid.")

        grid = Grid(floor_id=floor_id, name=name, cell_size=cell_size, status=GridStatus.DRAFT)
        grid = self._grid_repo.add(grid)

        self._generate_cells(grid, fp.width, fp.height, cell_size, walkable_mask)

        return grid

    def regenerate(self, grid_id: UUID) -> Grid:
        grid = self.get(grid_id)

        if grid.status == GridStatus.LOCKED:
            raise BusinessRuleViolation("Cannot regenerate a locked grid.")

        fp = self._floor_plan_repo.get_active(grid.floor_id)
        if fp is None:
            raise BusinessRuleViolation("An active FloorPlan is required to regenerate cells.")

        self._cell_repo.delete_by_grid(grid_id)
        self._generate_cells(grid, fp.width, fp.height, grid.cell_size)

        grid.touch()
        return self._grid_repo.update(grid)

    def lock(self, grid_id: UUID) -> Grid:
        grid = self.get(grid_id)

        if grid.status == GridStatus.LOCKED:
            raise BusinessRuleViolation("Grid is already locked.")

        grid.status = GridStatus.LOCKED
        grid.touch()
        return self._grid_repo.update(grid)

    def unlock(self, grid_id: UUID) -> Grid:
        grid = self.get(grid_id)

        if grid.status == GridStatus.DRAFT:
            raise BusinessRuleViolation("Draft grids are not locked.")

        if self._grid_repo.has_active(grid.floor_id) and grid.status != GridStatus.ACTIVE:
            raise BusinessRuleViolation("A floor can have only one active grid.")

        grid.status = GridStatus.ACTIVE if grid.status == GridStatus.LOCKED else GridStatus.DRAFT
        grid.touch()
        return self._grid_repo.update(grid)

    def activate(self, grid_id: UUID) -> Grid:
        grid = self.get(grid_id)

        if grid.status == GridStatus.ACTIVE:
            raise BusinessRuleViolation("Grid is already active.")

        if self._grid_repo.has_active(grid.floor_id):
            raise BusinessRuleViolation("A floor can have only one active grid.")

        grid.status = GridStatus.ACTIVE
        grid.touch()
        return self._grid_repo.update(grid)

    def list_cells(self, grid_id: UUID) -> list[Cell]:
        self.get(grid_id)
        return self._cell_repo.list_by_grid(grid_id)

    def update_walkable(self, cell_id: UUID, walkable: bool) -> Cell:
        cell = self._cell_repo.get(cell_id)
        if cell is None:
            raise LookupError("Cell not found.")

        grid = self.get(cell.grid_id)
        if self._campaign_repo.has_active_on_floor(grid.floor_id):
            raise BusinessRuleViolation(
                "Cannot modify cells while a Campaign is active on this floor."
            )

        cell.walkable = walkable
        cell.touch()
        return self._cell_repo.update(cell)

    def soft_delete(self, grid_id: UUID) -> None:
        grid = self.get(grid_id)
        if grid.status == GridStatus.ACTIVE:
            raise BusinessRuleViolation("Cannot delete an active grid.")
        self._cell_repo.delete_by_grid(grid_id)
        self._grid_repo.soft_delete(grid_id)

    def _generate_cells(
        self,
        grid: Grid,
        width: int,
        height: int,
        cell_size: int,
        walkable_mask: list[bool] | None = None,
    ) -> None:
        cols = math.ceil(width / cell_size)
        rows = math.ceil(height / cell_size)
        total = rows * cols
        if walkable_mask is not None and len(walkable_mask) != total:
            raise DomainValidationError(
                f"walkable_mask length {len(walkable_mask)} does not match {rows}x{cols} cells."
            )
        for row in range(rows):
            for column in range(cols):
                center_x = column * cell_size + cell_size / 2
                center_y = row * cell_size + cell_size / 2
                walkable = walkable_mask[row * cols + column] if walkable_mask is not None else True
                cell = Cell(
                    grid_id=grid.id,
                    row=row,
                    column=column,
                    center_x=center_x,
                    center_y=center_y,
                    walkable=walkable,
                )
                self._cell_repo.add(cell)

    def _require_floor(self, floor_id: UUID) -> None:
        if self._floor_repo.get(floor_id) is None:
            raise LookupError("Floor not found.")
