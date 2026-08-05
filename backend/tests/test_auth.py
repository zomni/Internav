from fastapi.testclient import TestClient

from tests.conftest import auth_header, login_admin


def test_login_success(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]
    assert body["data"]["user"]["role"] == "Administrator"


def test_login_wrong_password(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_email(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "Admin123!"},
    )
    assert resp.status_code == 401


def test_refresh_token_success(client: TestClient, seed_admin: None) -> None:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"},
    )
    refresh_token = login_resp.json()["data"]["refresh_token"]
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


def test_refresh_token_invalid(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client: TestClient, seed_admin: None) -> None:
    resp = client.get("/api/v1/organizations")
    assert resp.status_code == 200


def test_protected_post_requires_auth(client: TestClient, seed_admin: None) -> None:
    resp = client.post(
        "/api/v1/organizations",
        json={"name": "Test Org", "code": "TST"},
    )
    assert resp.status_code in (401, 403)


def test_protected_post_with_valid_token(client: TestClient, seed_admin: None) -> None:
    token = login_admin(client)
    resp = client.post(
        "/api/v1/organizations",
        json={"name": "Test Org", "code": "TST"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.json()["success"] is True
