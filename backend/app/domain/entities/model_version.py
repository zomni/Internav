from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import BusinessRuleViolation, DomainValidationError


class ModelVersionStatus(StrEnum):
    TRAINING = "Training"
    FAILED = "Failed"
    READY = "Ready"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


_VALID_MODEL_TRANSITIONS: dict[ModelVersionStatus, set[ModelVersionStatus]] = {
    ModelVersionStatus.TRAINING: {ModelVersionStatus.FAILED, ModelVersionStatus.READY},
    ModelVersionStatus.FAILED: set(),
    ModelVersionStatus.READY: {ModelVersionStatus.PUBLISHED, ModelVersionStatus.ARCHIVED},
    ModelVersionStatus.PUBLISHED: {ModelVersionStatus.ARCHIVED},
    ModelVersionStatus.ARCHIVED: set(),
}


@dataclass(kw_only=True)
class ModelVersion(AuditableEntity):
    dataset_id: UUID
    floor_id: UUID
    algorithm: str
    version: int = 1
    status: ModelVersionStatus = ModelVersionStatus.TRAINING
    hyperparameters: str | None = None
    metrics: str | None = None
    training_time: float | None = None
    checksum: str | None = None
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.algorithm.strip():
            raise DomainValidationError("ModelVersion algorithm is required.")

    def transition_to(self, target: ModelVersionStatus) -> None:
        allowed = _VALID_MODEL_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise BusinessRuleViolation(
                f"Cannot transition ModelVersion from {self.status.value} to {target.value}."
            )
        now = datetime.now(UTC)
        if target == ModelVersionStatus.PUBLISHED:
            self.published_at = now
        self.status = target
        self.touch()

    @property
    def is_immutable(self) -> bool:
        return self.status in (
            ModelVersionStatus.PUBLISHED,
            ModelVersionStatus.ARCHIVED,
        )
