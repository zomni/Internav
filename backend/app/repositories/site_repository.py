from typing import Protocol
from uuid import UUID

from app.domain.entities.site import Site
from app.repositories.base import Repository


class SiteRepository(Repository[Site], Protocol):
    def list_by_organization(self, organization_id: UUID) -> list[Site]: ...

    def list_all(self, is_active: bool | None = True) -> list[Site]: ...
