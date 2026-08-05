from typing import Protocol

from app.domain.entities.organization import Organization
from app.repositories.base import Repository


class OrganizationRepository(Repository[Organization], Protocol):
    def get_by_code(self, code: str) -> Organization | None: ...

    def list_all(self, is_active: bool | None = True) -> list[Organization]: ...
