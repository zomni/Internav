from uuid import UUID

from app.domain.entities.dataset_campaign import DatasetCampaign
from app.repositories.base import Repository


class DatasetCampaignRepository(Repository[DatasetCampaign]):
    def list_by_dataset(self, dataset_id: UUID) -> list[DatasetCampaign]: ...

    def list_campaign_ids(self, dataset_id: UUID) -> list[UUID]: ...

    def delete_by_dataset(self, dataset_id: UUID) -> None: ...
