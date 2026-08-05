from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class AuditableEntity:
    """Common identity, audit, version, activity and soft-delete state."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    version: int = 1
    is_active: bool = True

    def touch(self, updated_by: UUID | None = None) -> None:
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1

    def soft_delete(self, deleted_by: UUID | None = None) -> None:
        self.deleted_at = utc_now()
        self.is_active = False
        self.touch(deleted_by)
