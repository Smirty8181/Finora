import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["STAFF_USERNAME"] = "test-staff"
os.environ["STAFF_PASSWORD"] = "test-staff-password-for-ci"
os.environ["JWT_SECRET"] = "test-secret-with-more-than-32-bytes"
os.environ["FAQ_PATH"] = str(BACKEND_DIR.parent / "data" / "faq.json")

from app.main import app, engine, rate_limiter
from app.database import Base


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rate_limiter.limit = 30
    rate_limiter.requests.clear()
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def staff_headers(client):
    response = client.post(
        "/api/staff/login",
        json={"username": "test-staff", "password": "test-staff-password-for-ci"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
