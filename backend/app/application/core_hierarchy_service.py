from dataclasses import replace
from typing import TypeVar
from uuid import UUID

from app.domain.entities.building import Building
from app.domain.entities.floor import Floor
from app.domain.entities.organization import Organization
from app.domain.entities.site import Site
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.building_repository import BuildingRepository
from app.repositories.floor_repository import FloorRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.site_repository import SiteRepository


class CoreHierarchyService:
    """Application operations for the Organization -> Site -> Building -> Floor hierarchy."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        sites: SiteRepository,
        buildings: BuildingRepository,
        floors: FloorRepository,
    ) -> None:
        self._organizations = organizations
        self._sites = sites
        self._buildings = buildings
        self._floors = floors

    def create_organization(self, *, name: str, code: str, description: str | None) -> Organization:
        org = self._organizations.add(Organization(name=name, code=code, description=description))
        EventBus.publish(DomainEvent(EventType.ORGANIZATION_CREATED, org.id, {"name": name, "code": code}))
        return org

    def update_organization(self, entity_id: UUID, **changes: object) -> Organization:
        entity = self._require(self._organizations.get(entity_id), "Organization")
        updated = replace(entity, **changes)
        updated.touch()
        return self._organizations.update(updated)

    def list_organizations(self, is_active: bool | None = True) -> list[Organization]:
        return self._organizations.list_all(is_active)

    def get_organization(self, entity_id: UUID) -> Organization:
        return self._require(self._organizations.get(entity_id), "Organization")

    def delete_organization(self, entity_id: UUID) -> None:
        self._organizations.soft_delete(entity_id)

    def create_site(
        self,
        *,
        organization_id: UUID,
        name: str,
        code: str,
        timezone: str,
        address: str | None,
        metadata: str | None,
    ) -> Site:
        self.get_organization(organization_id)
        return self._sites.add(
            Site(
                organization_id=organization_id,
                name=name,
                code=code,
                timezone=timezone,
                address=address,
                metadata=metadata,
            )
        )

    def update_site(self, entity_id: UUID, **changes: object) -> Site:
        entity = self._require(self._sites.get(entity_id), "Site")
        updated = replace(entity, **changes)
        updated.touch()
        return self._sites.update(updated)

    def list_sites(self, is_active: bool | None = True) -> list[Site]:
        return self._sites.list_all(is_active)

    def get_site(self, entity_id: UUID) -> Site:
        return self._require(self._sites.get(entity_id), "Site")

    def delete_site(self, entity_id: UUID) -> None:
        self._sites.soft_delete(entity_id)

    def create_building(
        self, *, site_id: UUID, name: str, code: str, description: str | None
    ) -> Building:
        self.get_site(site_id)
        return self._buildings.add(
            Building(site_id=site_id, name=name, code=code, description=description)
        )

    def update_building(self, entity_id: UUID, **changes: object) -> Building:
        entity = self._require(self._buildings.get(entity_id), "Building")
        updated = replace(entity, **changes)
        updated.touch()
        return self._buildings.update(updated)

    def list_buildings(self, is_active: bool | None = True) -> list[Building]:
        return self._buildings.list_all(is_active)

    def get_building(self, entity_id: UUID) -> Building:
        return self._require(self._buildings.get(entity_id), "Building")

    def delete_building(self, entity_id: UUID) -> None:
        self._buildings.soft_delete(entity_id)

    def create_floor(
        self, *, building_id: UUID, name: str, level: int, display_order: int
    ) -> Floor:
        self.get_building(building_id)
        return self._floors.add(
            Floor(
                building_id=building_id,
                name=name,
                level=level,
                display_order=display_order,
            )
        )

    def update_floor(self, entity_id: UUID, **changes: object) -> Floor:
        entity = self._require(self._floors.get(entity_id), "Floor")
        updated = replace(entity, **changes)
        updated.touch()
        return self._floors.update(updated)

    def list_floors(self, is_active: bool | None = True) -> list[Floor]:
        return self._floors.list_all(is_active)

    def get_floor(self, entity_id: UUID) -> Floor:
        return self._require(self._floors.get(entity_id), "Floor")

    def delete_floor(self, entity_id: UUID) -> None:
        self._floors.soft_delete(entity_id)

    @staticmethod
    def _require(entity: "EntityT | None", entity_name: str) -> "EntityT":
        if entity is None:
            raise LookupError(f"{entity_name} not found.")
        return entity


EntityT = TypeVar("EntityT")
