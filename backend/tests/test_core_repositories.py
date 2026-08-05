from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.entities.building import Building
from app.domain.entities.floor import Floor
from app.domain.entities.organization import Organization
from app.domain.entities.site import Site
from app.domain.errors import BusinessRuleViolation
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.repositories.building_sqlalchemy_repository import (
    SqlAlchemyBuildingRepository,
)
from app.infrastructure.persistence.repositories.floor_sqlalchemy_repository import (
    SqlAlchemyFloorRepository,
)
from app.infrastructure.persistence.repositories.organization_sqlalchemy_repository import (
    SqlAlchemyOrganizationRepository,
)
from app.infrastructure.persistence.repositories.site_sqlalchemy_repository import (
    SqlAlchemySiteRepository,
)


def test_core_hierarchy_can_be_persisted_and_soft_deleted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session, session.begin():
        organizations = SqlAlchemyOrganizationRepository(session)
        sites = SqlAlchemySiteRepository(session)
        buildings = SqlAlchemyBuildingRepository(session)
        floors = SqlAlchemyFloorRepository(session)

        organization = organizations.add(Organization(name="Acme Hospital", code="ACME"))
        site = sites.add(
            Site(
                organization_id=organization.id,
                name="Central Site",
                code="CENTRAL",
                timezone="America/Santiago",
            )
        )
        building = buildings.add(Building(site_id=site.id, name="Main Building", code="MAIN"))
        floor = floors.add(Floor(building_id=building.id, name="Ground", level=0, display_order=1))

        assert organizations.get_by_code("ACME") == organization
        assert [item.id for item in sites.list_by_organization(organization.id)] == [site.id]
        assert [item.id for item in buildings.list_by_site(site.id)] == [building.id]
        assert [item.id for item in floors.list_by_building(building.id)] == [floor.id]

        floors.soft_delete(floor.id, uuid4())
        deleted_floor = floors.get(floor.id)
        assert deleted_floor is not None
        assert deleted_floor.is_active is False
        assert deleted_floor.deleted_at is not None


def test_organization_cannot_be_deleted_while_active_sites_exist() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session, session.begin():
        organizations = SqlAlchemyOrganizationRepository(session)
        sites = SqlAlchemySiteRepository(session)
        organization = organizations.add(Organization(name="Acme Hospital", code="ACME"))
        sites.add(
            Site(
                organization_id=organization.id,
                name="Central Site",
                code="CENTRAL",
                timezone="America/Santiago",
            )
        )

        with pytest.raises(BusinessRuleViolation):
            organizations.soft_delete(organization.id)
