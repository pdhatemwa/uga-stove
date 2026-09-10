import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB = Path("test_uga_stove.db").resolve()
TEST_EVIDENCE = Path("test_evidence").resolve()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["EVIDENCE_LOCAL_DIR"] = str(TEST_EVIDENCE)
os.environ["JWT_SECRET"] = "test-secret-with-at-least-thirty-two-characters"
os.environ["APP_ENV"] = "test"

from api.db import Base, SessionLocal, engine  # noqa: E402
from api.main import app  # noqa: E402
from api.models import DistributionPoint, User  # noqa: E402
from api.normalization import normalize_username  # noqa: E402
from api.permissions import Role  # noqa: E402
from api.security import hash_password  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def point(db):
    value = DistributionPoint(code="POINT-1", name="Official Point One")
    db.add(value)
    db.commit()
    db.refresh(value)
    return value


@pytest.fixture
def admin(db):
    value = User(
        username="admin",
        username_norm=normalize_username("admin"),
        full_name="Test Administrator",
        password_hash=hash_password("correct horse battery staple"),
        role=Role.ADMIN,
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return value


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client, admin):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def record_payload(point):
    return {
        "household_uid": "B-00001",
        "household_head_name": "Sample Household",
        "household_size": 6,
        "phone_number": "0700000000",
        "district": "Ntungamo",
        "subcounty": "Ntungamo",
        "parish": "Sample Parish",
        "village": "Sample Village",
        "serial_number": "PS-UG-M0001",
        "stove_type": "Improved Cook Stove",
        "stove_size": "Medium",
        "distribution_point_id": point.id,
        "distributed_on": "2026-09-01",
        "receiver_type": "Household Head",
        "receiver_name": "Sample Household",
        "carbon_waiver_accepted": True,
        "conditions_accepted": True,
        "ambassador_name": "Field Officer",
    }


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_EVIDENCE, ignore_errors=True)
