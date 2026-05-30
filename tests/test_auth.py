"""Auth API tests — requires PostgreSQL running and migrations applied."""

from fastapi.testclient import TestClient


def _auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_register_login_me_refresh_logout(client: TestClient, register_payload: dict) -> None:
    register = client.post("/api/v1/auth/register", json=register_payload)
    assert register.status_code == 201, register.text
    register_data = register.json()
    assert register_data["user"]["email"] == register_payload["email"]
    assert "access_token" in register_data["tokens"]
    assert "refresh_token" in register_data["tokens"]

    access = register_data["tokens"]["access_token"]
    refresh = register_data["tokens"]["refresh_token"]

    me = client.get("/api/v1/auth/me", headers=_auth_header(access))
    assert me.status_code == 200
    assert me.json()["email"] == register_payload["email"]

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
    )
    assert login.status_code == 200

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 200

    expired_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert expired_refresh.status_code == 401


def test_protected_users_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/users")
    assert response.status_code == 403
