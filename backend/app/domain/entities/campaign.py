from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import BusinessRuleViolation, DomainValidationError


class CampaignStatus(StrEnum):
    DRAFT = "Draft"
    READY = "Ready"
    COLLECTING = "Collecting"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


_VALID_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.READY},
    CampaignStatus.READY: {CampaignStatus.COLLECTING},
    CampaignStatus.COLLECTING: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED},
    CampaignStatus.PAUSED: {CampaignStatus.COLLECTING},
    CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
    CampaignStatus.ARCHIVED: set(),
}


@dataclass(kw_only=True)
class Campaign(AuditableEntity):
    floor_id: UUID
    name: str
    status: CampaignStatus = CampaignStatus.DRAFT
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Campaign name is required.")

    def transition_to(self, target: CampaignStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise BusinessRuleViolation(
                f"Cannot transition Campaign from {self.status.value} to {target.value}."
            )
        now = datetime.now(UTC)
        if target == CampaignStatus.COLLECTING and self.started_at is None:
            self.started_at = now
        if target in (CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED):
            self.finished_at = now
        self.status = target
        self.touch()

    @property
    def is_collecting(self) -> bool:
        return self.status == CampaignStatus.COLLECTING

    @property
    def accepts_fingerprints(self) -> bool:
        return self.status in (
            CampaignStatus.COLLECTING,
            CampaignStatus.PAUSED,
        )
