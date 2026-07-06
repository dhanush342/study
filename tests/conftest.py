"""Shared fixtures for pytest."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from backend.main import app
from backend.database import init_db, DB_PATH, close_all_connections


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure the test database is initialized and seeded before tests run."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()

    from backend.database import is_seeded
    if not is_seeded():
        from backend.seed import seed_database
        seed_database(DB_PATH)

    yield
    close_all_connections()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)
