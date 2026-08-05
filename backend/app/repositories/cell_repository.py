from uuid import UUID

from app.domain.entities.cell import Cell
from app.repositories.base import Repository


class CellRepository(Repository[Cell]):
    def list_by_grid(self, grid_id: UUID) -> list[Cell]: ...

    def has_by_row_column(self, grid_id: UUID, row: int, column: int) -> bool: ...

    def delete_by_grid(self, grid_id: UUID) -> None: ...
