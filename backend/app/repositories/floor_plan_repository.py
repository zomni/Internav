from uuid import UUID

from app.domain.entities.floor_plan import FloorPlan
from app.repositories.base import Repository


class FloorPlanRepository(Repository[FloorPlan]):
    def list_by_floor(self, floor_id: UUID) -> list[FloorPlan]: ...

    def get_active(self, floor_id: UUID) -> FloorPlan | None: ...

    def has_active(self, floor_id: UUID) -> bool: ...
