import hashlib
from pathlib import Path
from uuid import UUID

from app.domain.entities.base import utc_now
from app.domain.entities.floor_plan import FloorPlan
from app.domain.errors import BusinessRuleViolation
from app.repositories.cell_repository import CellRepository
from app.repositories.floor_plan_repository import FloorPlanRepository
from app.repositories.floor_repository import FloorRepository
from app.repositories.grid_repository import GridRepository

_EXTENSION_BY_MIME = {
    "image/svg+xml": "svg",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


class FloorPlanService:
    def __init__(
        self,
        floor_plan_repository: FloorPlanRepository,
        floor_repository: FloorRepository,
        grid_repository: GridRepository,
        cell_repository: CellRepository,
    ) -> None:
        self._floor_plan_repo = floor_plan_repository
        self._floor_repo = floor_repository
        self._grid_repo = grid_repository
        self._cell_repo = cell_repository

    def list_by_floor(self, floor_id: UUID) -> list[FloorPlan]:
        self._require_floor(floor_id)
        return self._floor_plan_repo.list_by_floor(floor_id)

    def get(self, floor_plan_id: UUID) -> FloorPlan:
        fp = self._floor_plan_repo.get(floor_plan_id)
        if fp is None:
            raise LookupError("FloorPlan not found.")
        return fp

    def upload(
        self,
        floor_id: UUID,
        image_bytes: bytes,
        mime_type: str,
        width: int,
        height: int,
        scale: float,
        upload_dir: str = "uploads",
    ) -> FloorPlan:
        self._require_floor(floor_id)
        if not image_bytes:
            raise BusinessRuleViolation("Empty FloorPlan image.")
        checksum = hashlib.sha256(image_bytes).hexdigest()
        version = self._next_version(floor_id)

        extension = _EXTENSION_BY_MIME.get(mime_type, "img")
        image_path = f"{upload_dir}/{floor_id}/v{version}.{extension}"
        path = Path(image_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)

        self._deactivate_existing(floor_id)

        entity = FloorPlan(
            floor_id=floor_id,
            image_path=image_path,
            width=width,
            height=height,
            scale=scale,
            checksum=checksum,
            mime_type=mime_type,
            version=version,
        )
        return self._floor_plan_repo.add(entity)

    def get_active(self, floor_id: UUID) -> FloorPlan | None:
        self._require_floor(floor_id)
        return self._floor_plan_repo.get_active(floor_id)

    def soft_delete(self, floor_plan_id: UUID) -> None:
        fp = self.get(floor_plan_id)
        if fp.is_active:
            raise BusinessRuleViolation("Cannot delete an active FloorPlan. Deactivate it first.")
        self._floor_plan_repo.soft_delete(floor_plan_id)

    def _require_floor(self, floor_id: UUID) -> None:
        if self._floor_repo.get(floor_id) is None:
            raise LookupError("Floor not found.")

    def _deactivate_existing(self, floor_id: UUID) -> None:
        active = self._floor_plan_repo.get_active(floor_id)
        if active is not None:
            active.is_active = False
            active.updated_at = utc_now()
            self._floor_plan_repo.update(active)

    def _next_version(self, floor_id: UUID) -> int:
        versions = self._floor_plan_repo.list_by_floor(floor_id)
        if not versions:
            return 1
        return max(fp.version for fp in versions) + 1
