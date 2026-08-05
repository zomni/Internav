from uuid import UUID

from app.domain.entities.campaign import Campaign
from app.repositories.base import Repository


class CampaignRepository(Repository[Campaign]):
    def list_all(self) -> list[Campaign]: ...

    def list_by_floor(self, floor_id: UUID) -> list[Campaign]: ...

    def has_active_on_floor(self, floor_id: UUID) -> bool: ...
