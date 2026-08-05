from uuid import UUID

from app.domain.entities.model_version import ModelVersion
from app.repositories.base import Repository


class ModelVersionRepository(Repository[ModelVersion]):
    def list_by_floor(self, floor_id: UUID) -> list[ModelVersion]: ...

    def list_by_dataset(self, dataset_id: UUID) -> list[ModelVersion]: ...

    def has_published_on_floor(self, floor_id: UUID) -> bool: ...

    def get_published_on_floor(self, floor_id: UUID) -> ModelVersion | None: ...
