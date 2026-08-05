from typing import Protocol
from uuid import UUID

from app.domain.entities.building import Building
from app.repositories.base import Repository


class BuildingRepository(Repository[Building], Protocol):
    def list_by_site(self, site_id: UUID) -> list[Building]: ...

    def list_all(self, is_active: bool | None = True) -> list[Building]: ...
