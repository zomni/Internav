import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.application.floor_plan_service import FloorPlanService
from app.domain.entities.floor import Floor
from app.domain.entities.floor_plan import FloorPlan
from app.domain.errors import BusinessRuleViolation


class FakeFloorRepo:
    def __init__(self):
        self._data: dict[UUID, Floor] = {}

    def get(self, fid: UUID) -> Floor | None:
        return self._data.get(fid)

    def add(self, f: Floor) -> Floor:
        self._data[f.id] = f
        return f


class FakeFloorPlanRepo:
    def __init__(self):
        self._data: dict[UUID, FloorPlan] = {}

    def get(self, fid: UUID) -> FloorPlan | None:
        return self._data.get(fid)

    def add(self, fp: FloorPlan) -> FloorPlan:
        self._data[fp.id] = fp
        return fp

    def update(self, fp: FloorPlan) -> FloorPlan:
        self._data[fp.id] = fp
        return fp

    def list_by_floor(self, floor_id: UUID) -> list[FloorPlan]:
        return [fp for fp in self._data.values() if fp.floor_id == floor_id]

    def get_active(self, floor_id: UUID) -> FloorPlan | None:
        for fp in self._data.values():
            if fp.floor_id == floor_id and fp.is_active:
                return fp
        return None

    def soft_delete(self, fid: UUID) -> None:
        if fid in self._data:
            del self._data[fid]


class FakeGridRepo:
    def list_by_floor(self, floor_id: UUID) -> list:
        return []

    def has_active(self, floor_id: UUID) -> bool:
        return False


class FakeCellRepo:
    def list_by_grid(self, grid_id: UUID) -> list:
        return []


class TestFloorPlanService:
    def setup_method(self):
        self.floor_repo = FakeFloorRepo()
        self.fp_repo = FakeFloorPlanRepo()
        self.grid_repo = FakeGridRepo()
        self.cell_repo = FakeCellRepo()
        self.upload_dir = tempfile.mkdtemp()
        self.service = FloorPlanService(self.fp_repo, self.floor_repo, self.grid_repo, self.cell_repo)

    def _add_floor(self) -> Floor:
        f = Floor(building_id=uuid4(), name="F1", level=0, display_order=1)
        self.floor_repo.add(f)
        return f

    def test_list_by_floor_returns_empty_when_no_plans(self):
        floor = self._add_floor()
        result = self.service.list_by_floor(floor.id)
        assert result == []

    def test_list_by_floor_raises_on_missing_floor(self):
        with pytest.raises(LookupError):
            self.service.list_by_floor(uuid4())

    def test_get_returns_plan(self):
        floor = self._add_floor()
        fp = self.fp_repo.add(FloorPlan(floor_id=floor.id, image_path="/img.png", width=100, height=200, scale=0.05, checksum="abc", mime_type="image/png"))
        result = self.service.get(fp.id)
        assert result.id == fp.id

    def test_get_raises_on_missing(self):
        with pytest.raises(LookupError):
            self.service.get(uuid4())

    def test_upload_creates_plan_with_checksum(self):
        floor = self._add_floor()
        fp = self.service.upload(floor.id, b"fake-image-data", "image/png", 100, 200, 0.05, self.upload_dir)
        assert fp.floor_id == floor.id
        assert fp.checksum == "28d81db19370f98fdc1d3e43fb1ef83a7cee62f3be86fed923d5f734da41319c"
        assert fp.version == 1

    def test_upload_increments_version(self):
        floor = self._add_floor()
        fp1 = self.service.upload(floor.id, b"data1", "image/png", 100, 200, 0.05, self.upload_dir)
        fp2 = self.service.upload(floor.id, b"data2", "image/png", 100, 200, 0.05, self.upload_dir)
        assert fp1.version == 1
        assert fp2.version == 2

    def test_upload_deactivates_previous(self):
        floor = self._add_floor()
        fp1 = self.service.upload(floor.id, b"data1", "image/png", 100, 200, 0.05, self.upload_dir)
        assert fp1.is_active is True
        self.service.upload(floor.id, b"data2", "image/png", 100, 200, 0.05, self.upload_dir)
        assert self.fp_repo.get(fp1.id).is_active is False

    def test_upload_raises_on_missing_floor(self):
        with pytest.raises(LookupError):
            self.service.upload(uuid4(), b"data", "image/png", 100, 200, 0.05, self.upload_dir)

    def test_upload_persists_image_file(self):
        floor = self._add_floor()
        fp = self.service.upload(floor.id, b"<svg width=\"40\" height=\"60\"/>", "image/svg+xml", 40, 60, 0.05, self.upload_dir)
        path = Path(fp.image_path)
        assert path.is_file()
        assert path.read_bytes() == b"<svg width=\"40\" height=\"60\"/>"

    def test_get_active_returns_none_when_no_active(self):
        floor = self._add_floor()
        assert self.service.get_active(floor.id) is None

    def test_get_active_returns_latest(self):
        floor = self._add_floor()
        fp = self.service.upload(floor.id, b"data", "image/png", 100, 200, 0.05, self.upload_dir)
        result = self.service.get_active(floor.id)
        assert result.id == fp.id

    def test_soft_delete_removes_plan(self):
        floor = self._add_floor()
        fp = self.fp_repo.add(FloorPlan(floor_id=floor.id, image_path="/img.png", width=100, height=200, scale=0.05, checksum="abc", mime_type="image/png", is_active=False))
        self.service.soft_delete(fp.id)
        assert self.fp_repo.get(fp.id) is None

    def test_soft_delete_raises_on_active(self):
        floor = self._add_floor()
        fp = self.fp_repo.add(FloorPlan(floor_id=floor.id, image_path="/img.png", width=100, height=200, scale=0.05, checksum="abc", mime_type="image/png", is_active=True))
        with pytest.raises(BusinessRuleViolation):
            self.service.soft_delete(fp.id)

    def test_soft_delete_raises_on_missing(self):
        with pytest.raises(LookupError):
            self.service.soft_delete(uuid4())
