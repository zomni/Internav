from __future__ import annotations

from typing import Protocol, TypeVar
from uuid import UUID

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    def add(self, entity: EntityT) -> EntityT: ...

    def get(self, entity_id: UUID) -> EntityT | None: ...

    def update(self, entity: EntityT) -> EntityT: ...

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None: ...
