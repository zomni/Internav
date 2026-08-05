from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin


def _create_org(client: TestClient, token: str) -> dict:
    resp = client.post(
        "/api/v1/organizations",
        json={"name": "Test Org", "code": "TST"},
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


def _setup_floor(client: TestClient, token: str) -> dict:
    org = _create_org(client, token)
    site = _create_site(client, token, org["id"])
    building = _create_building(client, token, site["id"])
    return _create_floor(client, token, building["id"])


def _create_campaign(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/campaigns",
        json={"name": "Test Campaign"},
        headers=auth_header(token),
    )
    return resp.json()["data"]


# ── Campaign Create & List ─────────────────────────────────────


def test_create_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/campaigns",
        json={"name": "My Campaign"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "My Campaign"
    assert data["status"] == "Draft"
    assert data["floor_id"] == floor["id"]


def test_list_campaigns(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _create_campaign(client, token, floor["id"])
    resp = client.get(f"/api/v1/floors/{floor['id']}/campaigns", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_get_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    resp = client.get(f"/api/v1/campaigns/{c['id']}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == c["id"]


def test_list_all_campaigns(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _create_campaign(client, token, floor["id"])
    resp = client.get("/api/v1/campaigns", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["floor_id"] == floor["id"]


def test_get_campaign_not_found(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.get(
        "/api/v1/campaigns/00000000-0000-0000-0000-000000000000",
        headers=auth_header(token),
    )
    assert resp.status_code == 404


# ── Campaign State Machine ──────────────────────────────────────


def test_full_lifecycle(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    cid = c["id"]

    r = client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Ready"

    r = client.patch(f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Collecting"
    assert r.json()["data"]["started_at"] is not None

    r = client.patch(f"/api/v1/campaigns/{cid}/pause", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Paused"

    r = client.patch(f"/api/v1/campaigns/{cid}/resume", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Collecting"

    r = client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Completed"
    assert r.json()["data"]["finished_at"] is not None

    r = client.patch(f"/api/v1/campaigns/{cid}/archive", headers=auth_header(token))
    assert r.json()["data"]["status"] == "Archived"


def test_invalid_transition(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    cid = c["id"]

    r = client.patch(f"/api/v1/campaigns/{cid}/pause", headers=auth_header(token))
    assert r.status_code == 409


# ── Campaign Delete Rules ───────────────────────────────────────


def test_delete_draft_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    resp = client.delete(f"/api/v1/campaigns/{c['id']}", headers=auth_header(token))
    assert resp.status_code == 204


def test_delete_active_campaign_rejected(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    client.patch(f"/api/v1/campaigns/{c['id']}/start", headers=auth_header(token))
    resp = client.delete(f"/api/v1/campaigns/{c['id']}", headers=auth_header(token))
    assert resp.status_code == 409


def test_delete_archived_campaign(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    c = _create_campaign(client, token, floor["id"])
    cid = c["id"]
    client.patch(f"/api/v1/campaigns/{cid}/start", headers=auth_header(token))
    client.patch(f"/api/v1/campaigns/{cid}/begin-collecting", headers=auth_header(token))
    client.patch(f"/api/v1/campaigns/{cid}/complete", headers=auth_header(token))
    client.patch(f"/api/v1/campaigns/{cid}/archive", headers=auth_header(token))
    resp = client.delete(f"/api/v1/campaigns/{cid}", headers=auth_header(token))
    assert resp.status_code == 204
