import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

REGISTER_PAYLOAD = {
    "email": f"pytest_{uuid.uuid4().hex[:8]}@example.com",
    "username": f"user_{uuid.uuid4().hex[:8]}",
    "password": "SecurePass123!",
    "gender": "male",
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def register_payload() -> dict[str, str]:
    return {
        "email": f"pytest_{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": "SecurePass123!",
        "gender": "male",
    }
