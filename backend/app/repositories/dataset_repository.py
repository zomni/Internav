from app.domain.entities.dataset import Dataset
from app.repositories.base import Repository


class DatasetRepository(Repository[Dataset]):
    def list_all(self) -> list[Dataset]: ...

    def get_next_version(self) -> int: ...
