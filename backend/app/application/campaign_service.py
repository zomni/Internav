from uuid import UUID

from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.errors import BusinessRuleViolation
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.floor_repository import FloorRepository


class CampaignService:
    def __init__(
        self,
        campaign_repository: CampaignRepository,
        floor_repository: FloorRepository,
    ) -> None:
        self._campaign_repo = campaign_repository
        self._floor_repo = floor_repository

    def list_all(self) -> list[Campaign]:
        return self._campaign_repo.list_all()

    def list_by_floor(self, floor_id: UUID) -> list[Campaign]:
        self._require_floor(floor_id)
        return self._campaign_repo.list_by_floor(floor_id)

    def get(self, campaign_id: UUID) -> Campaign:
        campaign = self._campaign_repo.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found.")
        return campaign

    def create(self, floor_id: UUID, name: str) -> Campaign:
        self._require_floor(floor_id)
        campaign = Campaign(floor_id=floor_id, name=name)
        return self._campaign_repo.add(campaign)

    def start(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.READY)
        return self._campaign_repo.update(campaign)

    def begin_collecting(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.COLLECTING)
        result = self._campaign_repo.update(campaign)
        EventBus.publish(
            DomainEvent(
                EventType.CAMPAIGN_STARTED, campaign_id, {"floor_id": str(campaign.floor_id)}
            )
        )
        return result

    def pause(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.PAUSED)
        return self._campaign_repo.update(campaign)

    def resume(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.COLLECTING)
        return self._campaign_repo.update(campaign)

    def complete(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.COMPLETED)
        return self._campaign_repo.update(campaign)

    def archive(self, campaign_id: UUID) -> Campaign:
        campaign = self.get(campaign_id)
        campaign.transition_to(CampaignStatus.ARCHIVED)
        return self._campaign_repo.update(campaign)

    def soft_delete(self, campaign_id: UUID) -> None:
        campaign = self.get(campaign_id)
        if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.ARCHIVED):
            raise BusinessRuleViolation(
                "Cannot delete a Campaign that is not in Draft or Archived status."
            )
        self._campaign_repo.soft_delete(campaign_id)

    def _require_floor(self, floor_id: UUID) -> None:
        if self._floor_repo.get(floor_id) is None:
            raise LookupError("Floor not found.")
