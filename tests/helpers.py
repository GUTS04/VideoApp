import uuid

from fastapi.testclient import TestClient


def register_user(
    client: TestClient,
    *,
    label: str,
    gender: str = "male",
) -> tuple[dict, str]:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"{label}_{suffix}@example.com",
        "username": f"{label}_{suffix}",
        "password": "SecurePass123!",
        "gender": gender,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["user"]["gender"] == gender
    return data["user"], data["tokens"]["access_token"]
