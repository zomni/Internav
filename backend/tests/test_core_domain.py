from uuid import uuid4

import pytest

from app.domain.entities.access_point_observation import AccessPointObservation
from app.domain.entities.building import Building
from app.domain.entities.campaign import Campaign, CampaignStatus
from app.domain.entities.cell import Cell
from app.domain.entities.dataset import Dataset, DatasetStatus
from app.domain.entities.floor import Floor
from app.domain.entities.floor_plan import FloorPlan
from app.domain.entities.grid import Grid, GridStatus
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.entities.organization import Organization
from app.domain.entities.site import Site
from app.domain.entities.user import User, UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

# ---------- Organization ----------


class TestOrganization:
    def test_valid_organization(self):
        org = Organization(name="Acme Hospital", code="ACME")
        assert org.name == "Acme Hospital"
        assert org.code == "ACME"
        assert org.is_active is True
        assert org.version == 1

    def test_name_too_short(self):
        with pytest.raises(DomainValidationError, match="Organization name length"):
            Organization(name="AB", code="ACME")

    def test_name_max_length(self):
        name = "X" * 120
        org = Organization(name=name, code="ACME")
        assert len(org.name) == 120

    def test_name_exceeds_max_length(self):
        with pytest.raises(DomainValidationError):
            Organization(name="X" * 121, code="ACME")

    def test_code_must_be_uppercase(self):
        with pytest.raises(DomainValidationError):
            Organization(name="Acme", code="acme")

    def test_code_empty(self):
        with pytest.raises(DomainValidationError):
            Organization(name="Acme", code="")

    def test_name_whitespace_stripped(self):
        org = Organization(name="  Acme Hospital  ", code="ACME")
        assert org.name.strip() == "Acme Hospital"

    def test_description_optional(self):
        org = Organization(name="Acme", code="ACME", description="Test")
        assert org.description == "Test"
        org2 = Organization(name="Acme", code="ACME")
        assert org2.description is None


# ---------- Site ----------


class TestSite:
    def test_valid_site(self):
        site = Site(organization_id=uuid4(), name="Central", code="CEN", timezone="UTC")
        assert site.name == "Central"

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Site name is required"):
            Site(organization_id=uuid4(), name=" ", code="CEN", timezone="UTC")

    def test_code_required(self):
        with pytest.raises(DomainValidationError, match="Site code is required"):
            Site(organization_id=uuid4(), name="Central", code="", timezone="UTC")

    def test_timezone_required(self):
        with pytest.raises(DomainValidationError, match="Site timezone is required"):
            Site(organization_id=uuid4(), name="Central", code="CEN", timezone=" ")

    def test_address_and_metadata_optional(self):
        site = Site(organization_id=uuid4(), name="Central", code="CEN", timezone="UTC", address="Addr", metadata="{}")
        assert site.address == "Addr"
        assert site.metadata == "{}"
        site2 = Site(organization_id=uuid4(), name="Central", code="CEN", timezone="UTC")
        assert site2.address is None
        assert site2.metadata is None


# ---------- Building ----------


class TestBuilding:
    def test_valid_building(self):
        b = Building(site_id=uuid4(), name="North Wing", code="NW")
        assert b.name == "North Wing"

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Building name is required"):
            Building(site_id=uuid4(), name="", code="NW")

    def test_code_required(self):
        with pytest.raises(DomainValidationError, match="Building code is required"):
            Building(site_id=uuid4(), name="North", code="")

    def test_description_optional(self):
        b = Building(site_id=uuid4(), name="North", code="NW", description="Desc")
        assert b.description == "Desc"
        b2 = Building(site_id=uuid4(), name="North", code="NW")
        assert b2.description is None


# ---------- Floor ----------


class TestFloor:
    def test_valid_floor(self):
        f = Floor(building_id=uuid4(), name="Ground", level=0, display_order=1)
        assert f.level == 0

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Floor name is required"):
            Floor(building_id=uuid4(), name="", level=0, display_order=1)

    def test_level_must_be_int(self):
        with pytest.raises(DomainValidationError, match="Floor level must be an integer"):
            Floor(building_id=uuid4(), name="Ground", level=1.5, display_order=1)

    def test_level_bool_rejected(self):
        with pytest.raises(DomainValidationError):
            Floor(building_id=uuid4(), name="Ground", level=True, display_order=1)

    def test_negative_level_allowed(self):
        f = Floor(building_id=uuid4(), name="B1", level=-1, display_order=0)
        assert f.level == -1


# ---------- FloorPlan ----------


class TestFloorPlan:
    def test_valid_floor_plan(self):
        fp = FloorPlan(
            floor_id=uuid4(), image_path="/img.png", width=100, height=200,
            scale=0.05, checksum="abc123", mime_type="image/png",
        )
        assert fp.width == 100
        assert fp.is_active is True

    def test_width_must_be_positive(self):
        with pytest.raises(DomainValidationError, match="FloorPlan width must be positive"):
            FloorPlan(floor_id=uuid4(), image_path="/img.png", width=0, height=200, scale=0.05, checksum="a", mime_type="image/png")

    def test_height_must_be_positive(self):
        with pytest.raises(DomainValidationError):
            FloorPlan(floor_id=uuid4(), image_path="/img.png", width=100, height=0, scale=0.05, checksum="a", mime_type="image/png")

    def test_scale_must_be_positive(self):
        with pytest.raises(DomainValidationError, match="FloorPlan scale must be positive"):
            FloorPlan(floor_id=uuid4(), image_path="/img.png", width=100, height=200, scale=0, checksum="a", mime_type="image/png")

    def test_image_path_required(self):
        with pytest.raises(DomainValidationError):
            FloorPlan(floor_id=uuid4(), image_path="", width=100, height=200, scale=0.05, checksum="a", mime_type="image/png")

    def test_checksum_required(self):
        with pytest.raises(DomainValidationError):
            FloorPlan(floor_id=uuid4(), image_path="/img.png", width=100, height=200, scale=0.05, checksum="", mime_type="image/png")

    def test_mime_type_required(self):
        with pytest.raises(DomainValidationError):
            FloorPlan(floor_id=uuid4(), image_path="/img.png", width=100, height=200, scale=0.05, checksum="a", mime_type="")

    def test_version_defaults(self):
        fp = FloorPlan(floor_id=uuid4(), image_path="/img.png", width=10, height=10, scale=0.1, checksum="a", mime_type="image/png")
        assert fp.version == 1

    def test_can_set_inactive(self):
        fp = FloorPlan(floor_id=uuid4(), image_path="/img.png", width=10, height=10, scale=0.1, checksum="a", mime_type="image/png", is_active=False)
        assert fp.is_active is False


# ---------- Grid ----------


class TestGrid:
    def test_valid_grid(self):
        g = Grid(floor_id=uuid4(), name="Main Grid", cell_size=10)
        assert g.status == GridStatus.DRAFT

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Grid name is required"):
            Grid(floor_id=uuid4(), name="", cell_size=10)

    def test_cell_size_must_be_positive(self):
        with pytest.raises(DomainValidationError, match="Grid cell_size must be positive"):
            Grid(floor_id=uuid4(), name="Grid", cell_size=0)

    def test_cell_size_must_be_int(self):
        with pytest.raises(DomainValidationError):
            Grid(floor_id=uuid4(), name="Grid", cell_size=1.5)

    def test_cell_size_bool_rejected(self):
        with pytest.raises(DomainValidationError):
            Grid(floor_id=uuid4(), name="Grid", cell_size=True)

    def test_status_enum(self):
        g = Grid(floor_id=uuid4(), name="Grid", cell_size=5, status=GridStatus.LOCKED)
        assert g.status == GridStatus.LOCKED


# ---------- Cell ----------


class TestCell:
    def test_valid_cell(self):
        c = Cell(grid_id=uuid4(), row=0, column=0, center_x=10.0, center_y=20.0)
        assert c.walkable is True

    def test_row_must_be_non_negative(self):
        with pytest.raises(DomainValidationError, match="Cell row must be non-negative"):
            Cell(grid_id=uuid4(), row=-1, column=0, center_x=0.0, center_y=0.0)

    def test_column_must_be_non_negative(self):
        with pytest.raises(DomainValidationError):
            Cell(grid_id=uuid4(), row=0, column=-1, center_x=0.0, center_y=0.0)

    def test_center_x_must_be_non_negative(self):
        with pytest.raises(DomainValidationError):
            Cell(grid_id=uuid4(), row=0, column=0, center_x=-1.0, center_y=0.0)

    def test_center_y_must_be_non_negative(self):
        with pytest.raises(DomainValidationError):
            Cell(grid_id=uuid4(), row=0, column=0, center_x=0.0, center_y=-1.0)

    def test_row_bool_rejected(self):
        with pytest.raises(DomainValidationError):
            Cell(grid_id=uuid4(), row=True, column=0, center_x=0.0, center_y=0.0)

    def test_column_bool_rejected(self):
        with pytest.raises(DomainValidationError):
            Cell(grid_id=uuid4(), row=0, column=True, center_x=0.0, center_y=0.0)

    def test_walkable_default_true(self):
        c = Cell(grid_id=uuid4(), row=0, column=0, center_x=0.0, center_y=0.0)
        assert c.walkable is True

    def test_walkable_false(self):
        c = Cell(grid_id=uuid4(), row=0, column=0, center_x=0.0, center_y=0.0, walkable=False)
        assert c.walkable is False


# ---------- Campaign ----------


class TestCampaign:
    def test_valid_campaign(self):
        c = Campaign(floor_id=uuid4(), name="Test Campaign")
        assert c.status == CampaignStatus.DRAFT
        assert c.is_collecting is False

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Campaign name is required"):
            Campaign(floor_id=uuid4(), name="")

    def test_accepts_fingerprints_in_collecting(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        c.transition_to(CampaignStatus.READY)
        c.transition_to(CampaignStatus.COLLECTING)
        assert c.accepts_fingerprints is True

    def test_accepts_fingerprints_in_paused(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        c.transition_to(CampaignStatus.READY)
        c.transition_to(CampaignStatus.COLLECTING)
        c.transition_to(CampaignStatus.PAUSED)
        assert c.accepts_fingerprints is True

    def test_rejects_fingerprints_in_draft(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        assert c.accepts_fingerprints is False

    def test_full_lifecycle(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        c.transition_to(CampaignStatus.READY)
        assert c.status == CampaignStatus.READY
        c.transition_to(CampaignStatus.COLLECTING)
        assert c.started_at is not None
        c.transition_to(CampaignStatus.PAUSED)
        assert c.status == CampaignStatus.PAUSED
        c.transition_to(CampaignStatus.COLLECTING)
        assert c.status == CampaignStatus.COLLECTING
        c.transition_to(CampaignStatus.COMPLETED)
        assert c.finished_at is not None
        c.transition_to(CampaignStatus.ARCHIVED)
        assert c.status == CampaignStatus.ARCHIVED

    def test_invalid_transition_from_draft(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        with pytest.raises(BusinessRuleViolation):
            c.transition_to(CampaignStatus.COLLECTING)

    def test_invalid_transition_from_archived(self):
        c = Campaign(floor_id=uuid4(), name="Test")
        c.transition_to(CampaignStatus.READY)
        c.transition_to(CampaignStatus.COLLECTING)
        c.transition_to(CampaignStatus.COMPLETED)
        c.transition_to(CampaignStatus.ARCHIVED)
        with pytest.raises(BusinessRuleViolation):
            c.transition_to(CampaignStatus.DRAFT)


# ---------- Dataset ----------


class TestDataset:
    def test_valid_dataset(self):
        d = Dataset(name="My Dataset")
        assert d.status == DatasetStatus.DRAFT
        assert d.dataset_version == 1

    def test_name_required(self):
        with pytest.raises(DomainValidationError, match="Dataset name is required"):
            Dataset(name="")

    def test_is_immutable_in_ready(self):
        d = Dataset(name="Test")
        d.transition_to(DatasetStatus.BUILDING)
        d.transition_to(DatasetStatus.READY)
        assert d.is_immutable is True

    def test_is_immutable_in_archived(self):
        d = Dataset(name="Test")
        d.transition_to(DatasetStatus.BUILDING)
        d.transition_to(DatasetStatus.READY)
        d.transition_to(DatasetStatus.ARCHIVED)
        assert d.is_immutable is True

    def test_not_immutable_in_draft(self):
        d = Dataset(name="Test")
        assert d.is_immutable is False

    def test_full_lifecycle(self):
        d = Dataset(name="Test")
        d.transition_to(DatasetStatus.BUILDING)
        assert d.status == DatasetStatus.BUILDING
        d.transition_to(DatasetStatus.READY)
        assert d.status == DatasetStatus.READY
        d.transition_to(DatasetStatus.ARCHIVED)
        assert d.status == DatasetStatus.ARCHIVED

    def test_invalid_transition_draft_to_ready(self):
        d = Dataset(name="Test")
        with pytest.raises(BusinessRuleViolation):
            d.transition_to(DatasetStatus.READY)

    def test_invalid_transition_archived_to_any(self):
        d = Dataset(name="Test")
        d.transition_to(DatasetStatus.BUILDING)
        d.transition_to(DatasetStatus.READY)
        d.transition_to(DatasetStatus.ARCHIVED)
        with pytest.raises(BusinessRuleViolation):
            d.transition_to(DatasetStatus.BUILDING)

    def test_metadata_defaults(self):
        d = Dataset(name="Test")
        assert d.fingerprint_count == 0
        assert d.observation_count == 0
        assert d.floor_count == 0


# ---------- ModelVersion ----------


class TestModelVersion:
    def test_valid_model_version(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        assert mv.status == ModelVersionStatus.TRAINING
        assert mv.version == 1

    def test_algorithm_required(self):
        with pytest.raises(DomainValidationError, match="ModelVersion algorithm is required"):
            ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="")

    def test_full_lifecycle(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        assert mv.status == ModelVersionStatus.READY
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        assert mv.published_at is not None
        mv.transition_to(ModelVersionStatus.ARCHIVED)
        assert mv.status == ModelVersionStatus.ARCHIVED

    def test_failed_transition(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        mv.transition_to(ModelVersionStatus.FAILED)
        assert mv.status == ModelVersionStatus.FAILED

    def test_is_immutable_in_published(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv.transition_to(ModelVersionStatus.PUBLISHED)
        assert mv.is_immutable is True

    def test_is_immutable_in_archived(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv.transition_to(ModelVersionStatus.ARCHIVED)
        assert mv.is_immutable is True

    def test_invalid_transition_training_to_published(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        with pytest.raises(BusinessRuleViolation):
            mv.transition_to(ModelVersionStatus.PUBLISHED)

    def test_invalid_transition_archived_to_ready(self):
        mv = ModelVersion(dataset_id=uuid4(), floor_id=uuid4(), algorithm="knn")
        mv.transition_to(ModelVersionStatus.READY)
        mv.transition_to(ModelVersionStatus.ARCHIVED)
        with pytest.raises(BusinessRuleViolation):
            mv.transition_to(ModelVersionStatus.READY)


# ---------- AccessPointObservation ----------


class TestAccessPointObservation:
    def test_valid_observation(self):
        obs = AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=-50, frequency=2400)
        assert obs.rssi == -50

    def test_bssid_required(self):
        with pytest.raises(DomainValidationError, match="AccessPointObservation bssid is required"):
            AccessPointObservation(fingerprint_id=uuid4(), bssid="", ssid="net", rssi=-50, frequency=2400)

    def test_rssi_below_min(self):
        with pytest.raises(DomainValidationError, match="AccessPointObservation rssi"):
            AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=-101, frequency=2400)

    def test_rssi_above_max(self):
        with pytest.raises(DomainValidationError):
            AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=1, frequency=2400)

    def test_rssi_boundary(self):
        obs1 = AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=-100, frequency=2400)
        assert obs1.rssi == -100
        obs2 = AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=0, frequency=2400)
        assert obs2.rssi == 0

    def test_frequency_must_be_positive(self):
        with pytest.raises(DomainValidationError, match="AccessPointObservation frequency must be positive"):
            AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=-50, frequency=0)

    def test_optional_fields_default(self):
        obs = AccessPointObservation(fingerprint_id=uuid4(), bssid="aa:bb", ssid="net", rssi=-50, frequency=5180)
        assert obs.channel == 0
        assert obs.band == ""
        assert obs.security == ""


# ---------- User ----------


class TestUser:
    def test_valid_user(self):
        u = User(email="test@test.com", password_hash="hash", role=UserRole.OPERATOR)
        assert u.email == "test@test.com"

    def test_email_missing_at(self):
        with pytest.raises(DomainValidationError, match="User email is required"):
            User(email="invalid", password_hash="hash", role=UserRole.VIEWER)

    def test_email_empty(self):
        with pytest.raises(DomainValidationError):
            User(email="", password_hash="hash", role=UserRole.VIEWER)

    def test_email_whitespace_only(self):
        with pytest.raises(DomainValidationError):
            User(email="   ", password_hash="hash", role=UserRole.VIEWER)

    def test_password_hash_required(self):
        with pytest.raises(DomainValidationError, match="User password hash is required"):
            User(email="test@test.com", password_hash="", role=UserRole.ADMINISTRATOR)

    def test_organization_id_optional(self):
        u = User(email="test@test.com", password_hash="hash", role=UserRole.OPERATOR)
        assert u.organization_id is None

    def test_can_set_organization(self):
        u = User(email="test@test.com", password_hash="hash", role=UserRole.VIEWER, organization_id=uuid4())
        assert u.organization_id is not None


# ---------- Soft delete ----------


class TestSoftDelete:
    def test_organization_soft_delete(self):
        org = Organization(name="Acme", code="ACME")
        org.soft_delete()
        assert org.deleted_at is not None
        assert org.is_active is False
        assert org.version == 2

    def test_site_soft_delete(self):
        site = Site(organization_id=uuid4(), name="Central", code="CEN", timezone="UTC")
        site.soft_delete()
        assert site.deleted_at is not None
        assert site.is_active is False

    def test_building_soft_delete(self):
        b = Building(site_id=uuid4(), name="North", code="NW")
        b.soft_delete()
        assert b.deleted_at is not None

    def test_soft_delete_twice(self):
        org = Organization(name="Acme", code="ACME")
        org.soft_delete()
        v1 = org.version
        org.soft_delete()
        assert org.version == v1 + 1

    def test_floor_soft_delete(self):
        f = Floor(building_id=uuid4(), name="Ground", level=0, display_order=1)
        f.soft_delete()
        assert f.deleted_at is not None
        assert f.is_active is False
