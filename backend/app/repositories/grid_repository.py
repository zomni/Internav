from uuid import UUID

from app.domain.entities.grid import Grid
from app.repositories.base import Repository


class GridRepository(Repository[Grid]):
    def list_all(self) -> list[Grid]: ...

    def list_by_floor(self, floor_id: UUID) -> list[Grid]: ...

    def get_active(self, floor_id: UUID) -> Grid | None: ...

    def has_active(self, floor_id: UUID) -> bool: ...
