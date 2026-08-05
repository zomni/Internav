from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin

BOX_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="3000">'
    b'<rect width="2000" height="3000" fill="white"/>'
    b'<rect x="200" y="200" width="1600" height="2600" fill="none" stroke="black"/>'
    b"</svg>"
)


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


def _upload_floor_plan(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/floor-plans",
        files={"file": ("plan.svg", BOX_SVG, "image/svg+xml")},
        headers=auth_header(token),
    )
    return resp.json()["data"]


# ── Grid Generate ─────────────────────────────────────────────


def test_generate_grid(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Main Grid"
    assert data["cell_size"] == 50
    assert data["status"] == "Draft"


def test_generate_grid_requires_floor_plan(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_generate_grid_with_walkability_analysis(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Masked Grid", "cell_size": 100, "analyze_walkability": True},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    grid_id = resp.json()["data"]["id"]
    cells_resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    cells = cells_resp.json()["data"]
    assert len(cells) == 600
    assert any(not c["walkable"] for c in cells)
    assert any(c["walkable"] for c in cells)


def test_generate_grid_analyze_requires_active_plan(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50, "analyze_walkability": True},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


def test_generate_grid_only_one_active(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Grid 1", "cell_size": 50},
        headers=auth_header(token),
    )
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Grid 2", "cell_size": 50},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Grid Operations ───────────────────────────────────────────


def test_grid_operations_flow(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]

    resp = client.post(f"/api/v1/grids/{grid_id}/activate", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Active"

    resp = client.post(f"/api/v1/grids/{grid_id}/lock", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Locked"

    resp = client.post(f"/api/v1/grids/{grid_id}/unlock", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Active"


def test_lock_draft_grid_fails(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    resp = client.post(f"/api/v1/grids/{grid_id}/lock", headers=auth_header(token))
    assert resp.status_code == 200


def test_unlock_draft_grid_fails(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    resp = client.post(f"/api/v1/grids/{grid_id}/unlock", headers=auth_header(token))
    assert resp.status_code == 409


# ── Cell Operations ───────────────────────────────────────────


def test_cells_generated(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    assert resp.status_code == 200
    cells = resp.json()["data"]
    assert len(cells) > 0
    assert all(c["walkable"] is True for c in cells)


def test_regenerate_cells(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    client.post(f"/api/v1/grids/{grid_id}/activate", headers=auth_header(token))
    client.post(f"/api/v1/grids/{grid_id}/lock", headers=auth_header(token))
    client.post(f"/api/v1/grids/{grid_id}/unlock", headers=auth_header(token))

    resp = client.post(f"/api/v1/grids/{grid_id}/regenerate", headers=auth_header(token))
    assert resp.status_code == 200


def test_update_walkable(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    cells_resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    cell_id = cells_resp.json()["data"][0]["id"]

    resp = client.put(
        f"/api/v1/cells/{cell_id}/walkable",
        json={"walkable": False},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["walkable"] is False


def test_update_walkable_active_grid_allowed_without_campaign(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    client.post(f"/api/v1/grids/{grid_id}/activate", headers=auth_header(token))
    cells_resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    cell_id = cells_resp.json()["data"][0]["id"]
    resp = client.put(
        f"/api/v1/cells/{cell_id}/walkable",
        json={"walkable": False},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["walkable"] is False


def test_update_walkable_blocked_while_campaign_active(
    client: TestClient, seed_admin: None
) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    client.post(f"/api/v1/grids/{grid_id}/activate", headers=auth_header(token))
    camp_resp = client.post(
        f"/api/v1/floors/{floor['id']}/campaigns",
        json={"name": "Active Campaign"},
        headers=auth_header(token),
    )
    campaign_id = camp_resp.json()["data"]["id"]
    client.patch(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_header(token))
    cells_resp = client.get(f"/api/v1/grids/{grid_id}/cells", headers=auth_header(token))
    cell_id = cells_resp.json()["data"][0]["id"]
    resp = client.put(
        f"/api/v1/cells/{cell_id}/walkable",
        json={"walkable": False},
        headers=auth_header(token),
    )
    assert resp.status_code == 409


# ── Grid List / Get / Delete ─────────────────────────────────


def test_list_grids(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    resp = client.get(f"/api/v1/floors/{floor['id']}/grids", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


def test_list_all_grids(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    resp = client.get("/api/v1/grids", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Main Grid"


def test_get_grid(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    resp = client.get(f"/api/v1/grids/{grid_id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == grid_id


def test_delete_grid(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    resp = client.delete(f"/api/v1/grids/{grid_id}", headers=auth_header(token))
    assert resp.status_code == 204


def test_generate_after_delete_grid(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Grid 1", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    assert client.delete(f"/api/v1/grids/{grid_id}", headers=auth_header(token)).status_code == 204
    resp = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Grid 2", "cell_size": 50},
        headers=auth_header(token),
    )
    assert resp.status_code == 201


def test_delete_active_grid_fails(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    floor = _setup_floor(client, token)
    _upload_floor_plan(client, token, floor["id"])
    r = client.post(
        f"/api/v1/floors/{floor['id']}/grids",
        json={"name": "Main Grid", "cell_size": 50},
        headers=auth_header(token),
    )
    grid_id = r.json()["data"]["id"]
    client.post(f"/api/v1/grids/{grid_id}/activate", headers=auth_header(token))
    resp = client.delete(f"/api/v1/grids/{grid_id}", headers=auth_header(token))
    assert resp.status_code == 409
