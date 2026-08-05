from dataclasses import dataclass
from enum import StrEnum

from app.domain.entities.base import AuditableEntity
from app.domain.errors import BusinessRuleViolation, DomainValidationError


class DatasetStatus(StrEnum):
    DRAFT = "Draft"
    BUILDING = "Building"
    READY = "Ready"
    ARCHIVED = "Archived"


_VALID_DATASET_TRANSITIONS: dict[DatasetStatus, set[DatasetStatus]] = {
    DatasetStatus.DRAFT: {DatasetStatus.BUILDING},
    DatasetStatus.BUILDING: {DatasetStatus.READY},
    DatasetStatus.READY: {DatasetStatus.ARCHIVED},
    DatasetStatus.ARCHIVED: set(),
}


@dataclass(kw_only=True)
class Dataset(AuditableEntity):
    name: str
    status: DatasetStatus = DatasetStatus.DRAFT
    fingerprint_count: int = 0
    observation_count: int = 0
    floor_count: int = 0
    dataset_version: int = 1

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Dataset name is required.")

    def transition_to(self, target: DatasetStatus) -> None:
        allowed = _VALID_DATASET_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise BusinessRuleViolation(
                f"Cannot transition Dataset from {self.status.value} to {target.value}."
            )
        self.status = target
        self.touch()

    @property
    def is_immutable(self) -> bool:
        return self.status in (DatasetStatus.READY, DatasetStatus.ARCHIVED)
