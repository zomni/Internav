from uuid import UUID

from app.ai.training_pipeline import TrainingPipelineService
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.errors import BusinessRuleViolation
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.floor_repository import FloorRepository
from app.repositories.model_version_repository import ModelVersionRepository


class ModelVersionService:
    def __init__(
        self,
        model_version_repository: ModelVersionRepository,
        dataset_repository: DatasetRepository,
        floor_repository: FloorRepository,
        training_pipeline: TrainingPipelineService | None = None,
    ) -> None:
        self._model_version_repo = model_version_repository
        self._dataset_repo = dataset_repository
        self._floor_repo = floor_repository
        self._training_pipeline = training_pipeline

    def list_all(self) -> list[ModelVersion]:
        return self._model_version_repo.list_all()

    def get(self, model_version_id: UUID) -> ModelVersion:
        mv = self._model_version_repo.get(model_version_id)
        if mv is None:
            raise LookupError("ModelVersion not found.")
        return mv

    def list_by_floor(self, floor_id: UUID) -> list[ModelVersion]:
        self._require_floor_exists(floor_id)
        return self._model_version_repo.list_by_floor(floor_id)

    def list_by_dataset(self, dataset_id: UUID) -> list[ModelVersion]:
        self._require_dataset_exists(dataset_id)
        return self._model_version_repo.list_by_dataset(dataset_id)

    def create(
        self,
        dataset_id: UUID,
        floor_id: UUID,
        algorithm: str,
        hyperparameters: str | None = None,
    ) -> ModelVersion:
        self._require_dataset_exists(dataset_id)
        self._require_floor_exists(floor_id)
        mv = ModelVersion(
            dataset_id=dataset_id,
            floor_id=floor_id,
            algorithm=algorithm,
            hyperparameters=hyperparameters,
        )
        return self._model_version_repo.add(mv)

    def train(self, model_version_id: UUID) -> ModelVersion:
        if self._training_pipeline is None:
            raise RuntimeError("Training pipeline not configured.")
        return self._training_pipeline.train(model_version_id)

    def mark_ready(
        self,
        model_version_id: UUID,
        metrics: str | None = None,
        training_time: float | None = None,
        checksum: str | None = None,
    ) -> ModelVersion:
        mv = self.get(model_version_id)
        if mv.is_immutable:
            raise BusinessRuleViolation(
                f"Cannot modify a ModelVersion in {mv.status.value} status."
            )
        mv.transition_to(ModelVersionStatus.READY)
        mv.metrics = metrics
        mv.training_time = training_time
        mv.checksum = checksum
        return self._model_version_repo.update(mv)

    def mark_failed(self, model_version_id: UUID) -> ModelVersion:
        mv = self.get(model_version_id)
        if mv.is_immutable:
            raise BusinessRuleViolation(
                f"Cannot modify a ModelVersion in {mv.status.value} status."
            )
        mv.transition_to(ModelVersionStatus.FAILED)
        return self._model_version_repo.update(mv)

    def publish(self, model_version_id: UUID) -> ModelVersion:
        mv = self.get(model_version_id)
        if mv.status != ModelVersionStatus.READY:
            raise BusinessRuleViolation(
                f"Cannot publish a ModelVersion in {mv.status.value} status."
            )
        if self._model_version_repo.has_published_on_floor(mv.floor_id):
            raise BusinessRuleViolation(
                "Only one published model per floor is allowed. "
                "Unpublish the current model before publishing a new one."
            )
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        result = self._model_version_repo.update(mv)
        EventBus.publish(
            DomainEvent(
                EventType.MODEL_PUBLISHED,
                model_version_id,
                {
                    "floor_id": str(mv.floor_id),
                    "dataset_id": str(mv.dataset_id),
                    "algorithm": mv.algorithm,
                },
            )
        )
        return result

    def unpublish(self, model_version_id: UUID) -> ModelVersion:
        mv = self.get(model_version_id)
        if mv.status != ModelVersionStatus.PUBLISHED:
            raise BusinessRuleViolation("Can only unpublish a ModelVersion in Published status.")
        mv.transition_to(ModelVersionStatus.ARCHIVED)
        return self._model_version_repo.update(mv)

    def archive(self, model_version_id: UUID) -> ModelVersion:
        mv = self.get(model_version_id)
        if mv.status not in (ModelVersionStatus.READY, ModelVersionStatus.PUBLISHED):
            raise BusinessRuleViolation(
                f"Cannot archive a ModelVersion in {mv.status.value} status."
            )
        mv.transition_to(ModelVersionStatus.ARCHIVED)
        return self._model_version_repo.update(mv)

    def soft_delete(self, model_version_id: UUID) -> None:
        mv = self.get(model_version_id)
        if mv.is_immutable:
            raise BusinessRuleViolation(
                "Cannot delete a ModelVersion that is Published or Archived."
            )
        self._model_version_repo.soft_delete(model_version_id)

    def get_artifact_paths(self, model_version_id: UUID) -> dict[str, str]:
        mv = self.get(model_version_id)
        if mv.status not in (
            ModelVersionStatus.READY,
            ModelVersionStatus.PUBLISHED,
            ModelVersionStatus.ARCHIVED,
        ):
            raise BusinessRuleViolation(
                f"No artifacts for ModelVersion in {mv.status.value} status."
            )
        if self._training_pipeline is None:
            raise RuntimeError("Training pipeline not configured.")
        return self._training_pipeline.get_artifact_paths(model_version_id)

    def get_mobile_bundle(self, model_version_id: UUID) -> dict:
        mv = self.get(model_version_id)
        if mv.status not in (
            ModelVersionStatus.READY,
            ModelVersionStatus.PUBLISHED,
            ModelVersionStatus.ARCHIVED,
        ):
            raise BusinessRuleViolation(
                f"No artifacts for ModelVersion in {mv.status.value} status."
            )
        if self._training_pipeline is None:
            raise RuntimeError("Training pipeline not configured.")
        return self._training_pipeline.get_mobile_bundle(model_version_id)

    def _require_dataset_exists(self, dataset_id: UUID) -> None:
        if self._dataset_repo.get(dataset_id) is None:
            raise LookupError("Dataset not found.")

    def _require_floor_exists(self, floor_id: UUID) -> None:
        if self._floor_repo.get(floor_id) is None:
            raise LookupError("Floor not found.")
