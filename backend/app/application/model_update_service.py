from uuid import UUID

from app.domain.entities.model_version import ModelVersion
from app.repositories.floor_repository import FloorRepository
from app.repositories.model_version_repository import ModelVersionRepository


class ModelUpdateService:
    def __init__(
        self,
        model_version_repository: ModelVersionRepository,
        floor_repository: FloorRepository,
    ) -> None:
        self._model_version_repo = model_version_repository
        self._floor_repo = floor_repository

    def get_published_model(self, floor_id: UUID) -> ModelVersion | None:
        self._require_floor(floor_id)
        return self._model_version_repo.get_published_on_floor(floor_id)

    def check_for_update(
        self,
        floor_id: UUID,
        current_model_version_id: str | None = None,
    ) -> dict:
        self._require_floor(floor_id)
        published = self._model_version_repo.get_published_on_floor(floor_id)
        if published is None:
            return {"update_available": False, "model": None}
        if current_model_version_id is not None and str(published.id) == current_model_version_id:
            return {"update_available": False, "model": None}
        return {
            "update_available": True,
            "model": {
                "id": str(published.id),
                "version": published.version,
                "algorithm": published.algorithm,
                "checksum": published.checksum,
                "published_at": published.published_at.isoformat() if published.published_at else None,
            },
        }

    def _require_floor(self, floor_id: UUID) -> None:
        if self._floor_repo.get(floor_id) is None:
            raise LookupError("Floor not found.")
