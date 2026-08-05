from uuid import UUID

from app.domain.entities.campaign import CampaignStatus
from app.domain.entities.dataset import Dataset, DatasetStatus
from app.domain.entities.dataset_campaign import DatasetCampaign
from app.domain.errors import BusinessRuleViolation
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.cell_repository import CellRepository
from app.repositories.dataset_campaign_repository import DatasetCampaignRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.fingerprint_repository import FingerprintRepository


class DatasetService:
    def __init__(
        self,
        dataset_repository: DatasetRepository,
        dataset_campaign_repository: DatasetCampaignRepository,
        campaign_repository: CampaignRepository,
        fingerprint_repository: FingerprintRepository,
        cell_repository: CellRepository,
    ) -> None:
        self._dataset_repo = dataset_repository
        self._dataset_campaign_repo = dataset_campaign_repository
        self._campaign_repo = campaign_repository
        self._fingerprint_repo = fingerprint_repository
        self._cell_repo = cell_repository

    def list_all(self) -> list[Dataset]:
        return self._dataset_repo.list_all()

    def get(self, dataset_id: UUID) -> Dataset:
        dataset = self._dataset_repo.get(dataset_id)
        if dataset is None:
            raise LookupError("Dataset not found.")
        return dataset

    def create(self, name: str) -> Dataset:
        dataset = Dataset(name=name)
        return self._dataset_repo.add(dataset)

    def add_campaigns(self, dataset_id: UUID, campaign_ids: list[UUID]) -> Dataset:
        dataset = self.get(dataset_id)
        if dataset.is_immutable:
            raise BusinessRuleViolation(
                f"Cannot modify a Dataset in {dataset.status.value} status."
            )

        for cid in campaign_ids:
            campaign = self._campaign_repo.get(cid)
            if campaign is None:
                raise LookupError(f"Campaign {cid} not found.")
            if campaign.status != CampaignStatus.COMPLETED:
                raise BusinessRuleViolation(
                    f"Campaign {cid} must be Completed to include in a Dataset."
                )

            existing = self._dataset_campaign_repo.list_by_dataset(dataset_id)
            if any(dc.campaign_id == cid for dc in existing):
                raise BusinessRuleViolation(f"Campaign {cid} is already in this Dataset.")

            dc = DatasetCampaign(dataset_id=dataset_id, campaign_id=cid)
            self._dataset_campaign_repo.add(dc)

        self._recalculate_metadata(dataset_id)
        return self.get(dataset_id)

    def build(self, dataset_id: UUID) -> Dataset:
        dataset = self.get(dataset_id)
        campaign_ids = self._dataset_campaign_repo.list_campaign_ids(dataset_id)
        if not campaign_ids:
            raise BusinessRuleViolation("Cannot build a Dataset with no campaigns.")
        self._recalculate_metadata(dataset_id)
        dataset.transition_to(DatasetStatus.BUILDING)
        dataset = self._dataset_repo.update(dataset)
        dataset.transition_to(DatasetStatus.READY)
        dataset.dataset_version += 1
        result = self._dataset_repo.update(dataset)
        EventBus.publish(DomainEvent(EventType.DATASET_BUILT, dataset_id, {
            "name": result.name,
            "version": result.dataset_version,
            "fingerprint_count": result.fingerprint_count,
            "floor_count": result.floor_count,
        }))
        return result

    def archive(self, dataset_id: UUID) -> Dataset:
        dataset = self.get(dataset_id)
        dataset.transition_to(DatasetStatus.ARCHIVED)
        return self._dataset_repo.update(dataset)

    def soft_delete(self, dataset_id: UUID) -> None:
        dataset = self.get(dataset_id)
        if dataset.status not in (DatasetStatus.DRAFT, DatasetStatus.ARCHIVED):
            raise BusinessRuleViolation(
                "Cannot delete a Dataset that is not in Draft or Archived status."
            )
        self._dataset_repo.soft_delete(dataset_id)

    def _recalculate_metadata(self, dataset_id: UUID) -> None:
        dataset = self.get(dataset_id)
        campaign_ids = self._dataset_campaign_repo.list_campaign_ids(dataset_id)

        fingerprint_total = 0
        floor_ids: set[UUID] = set()

        for cid in campaign_ids:
            campaign = self._campaign_repo.get(cid)
            if campaign:
                floor_ids.add(campaign.floor_id)
            count = self._fingerprint_repo.count_by_campaign(cid)
            fingerprint_total += count

        dataset.fingerprint_count = fingerprint_total
        dataset.observation_count = 0
        dataset.floor_count = len(floor_ids)
        self._dataset_repo.update(dataset)
