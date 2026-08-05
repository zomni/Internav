from typing import Protocol
from uuid import UUID

from app.domain.entities.floor import Floor
from app.repositories.base import Repository


class FloorRepository(Repository[Floor], Protocol):
    def list_by_building(self, building_id: UUID) -> list[Floor]: ...

    def list_all(self, is_active: bool | None = True) -> list[Floor]: ...
