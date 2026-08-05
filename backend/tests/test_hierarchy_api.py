from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin


def _create_org(client: TestClient, token: str, code: str = "TST") -> dict:
    resp = client.post(
        "/api/v1/organizations",
        json={"name": f"Org {code}", "code": code},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_site(client: TestClient, token: str, org_id: str) -> dict:
    resp = client.post(
        "/api/v1/sites",
        json={
            "organization_id": org_id,
            "name": "Main Site",
            "code": "MAIN",
            "timezone": "America/Santiago",
        },
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_building(client: TestClient, token: str, site_id: str) -> dict:
    resp = client.post(
        "/api/v1/buildings",
        json={"site_id": site_id, "name": "North Wing", "code": "NW"},
        headers=auth_header(token),
    )
    return resp.json()["data"]


def _create_floor(client: TestClient, token: str, building_id: str) -> dict:
    resp = client.post(
        "/api/v1/floors",
        json={"building_id": building_id, "name": "Ground", "level": 0, "display_order": 1},
        headers=auth_header(token),
    )
    return resp.json()["data"]


# ── Organization CRUD ──────────────────────────────────────────


def test_create_organization(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    data = _create_org(client, token)
    assert data["code"] == "TST"
    assert data["name"] == "Org TST"


def test_list_organizations(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    _create_org(client, token)
    _create_org(client, token, "TST2")
    resp = client.get("/api/v1/organizations", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2


def test_get_organization(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    resp = client.get(f"/api/v1/organizations/{org['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["code"] == "TST"


def test_get_organization_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_update_organization(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    resp = client.put(
        f"/api/v1/organizations/{org['id']}",
        json={"name": "Updated Org"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Org"


def test_delete_organization(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    resp = client.delete(f"/api/v1/organizations/{org['id']}", headers=auth_header(token))
    assert resp.status_code == 204


# ── Site CRUD ──────────────────────────────────────────────────


def test_create_site(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    assert site["code"] == "MAIN"
    assert site["organization_id"] == org["id"]


def test_create_site_missing_parent(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/sites",
        json={
            "organization_id": "00000000-0000-0000-0000-000000000000",
            "name": "Orphan",
            "code": "ORPH",
            "timezone": "UTC",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_list_sites(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    _create_site(client, token, org["id"])
    resp = client.get("/api/v1/sites", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_update_site(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    resp = client.put(
        f"/api/v1/sites/{site['id']}",
        json={"name": "Updated Site"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Updated Site"


def test_delete_site(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    resp = client.delete(f"/api/v1/sites/{site['id']}", headers=auth_header(token))
    assert resp.status_code == 204


# ── Building CRUD ──────────────────────────────────────────────


def test_create_building(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    assert building["code"] == "NW"


def test_create_building_missing_parent(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/buildings",
        json={"site_id": "00000000-0000-0000-0000-000000000000", "name": "Ghost", "code": "GH"},
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_list_buildings(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    _create_building(client, token, site["id"])
    resp = client.get("/api/v1/buildings", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_update_building(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    resp = client.put(
        f"/api/v1/buildings/{building['id']}",
        json={"name": "South Wing"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "South Wing"


def test_delete_building(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    resp = client.delete(f"/api/v1/buildings/{building['id']}", headers=auth_header(token))
    assert resp.status_code == 204


# ── Floor CRUD ─────────────────────────────────────────────────


def test_create_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    floor = _create_floor(client, token, building["id"])
    assert floor["level"] == 0
    assert floor["name"] == "Ground"


def test_create_floor_missing_parent(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/floors",
        json={
            "building_id": "00000000-0000-0000-0000-000000000000",
            "name": "B1",
            "level": -1,
            "display_order": 1,
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 404


def test_list_floors(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    _create_floor(client, token, building["id"])
    resp = client.get("/api/v1/floors", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_update_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    floor = _create_floor(client, token, building["id"])
    resp = client.put(
        f"/api/v1/floors/{floor['id']}",
        json={"name": "Level 1", "level": 1},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Level 1"


def test_delete_floor(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    floor = _create_floor(client, token, building["id"])
    resp = client.delete(f"/api/v1/floors/{floor['id']}", headers=auth_header(token))
    assert resp.status_code == 204


# ── Full hierarchy lifecycle ───────────────────────────────────


def test_full_hierarchy_lifecycle(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    floor = _create_floor(client, token, building["id"])

    assert (
        client.get(f"/api/v1/organizations/{org['id']}", headers=auth_header(token)).status_code
        == 200
    )
    assert client.get(f"/api/v1/sites/{site['id']}", headers=auth_header(token)).status_code == 200
    assert (
        client.get(f"/api/v1/buildings/{building['id']}", headers=auth_header(token)).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/floors/{floor['id']}", headers=auth_header(token)).status_code == 200
    )

    assert (
        client.delete(f"/api/v1/floors/{floor['id']}", headers=auth_header(token)).status_code
        == 204
    )
    assert (
        client.delete(f"/api/v1/buildings/{building['id']}", headers=auth_header(token)).status_code
        == 204
    )
    assert (
        client.delete(f"/api/v1/sites/{site['id']}", headers=auth_header(token)).status_code == 204
    )
    assert (
        client.delete(f"/api/v1/organizations/{org['id']}", headers=auth_header(token)).status_code
        == 204
    )
