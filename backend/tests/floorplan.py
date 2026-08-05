"""Shared floor-plan fixtures for API tests."""

from fastapi.testclient import TestClient

FLOORPLAN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="90">'
    b'<rect width="120" height="90" fill="white"/>'
    b"</svg>"
)


def upload_floor_plan(client: TestClient, token: str, floor_id: str) -> dict:
    resp = client.post(
        f"/api/v1/floors/{floor_id}/floor-plans",
        files={"file": ("plan.svg", FLOORPLAN_SVG, "image/svg+xml")},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["data"]
