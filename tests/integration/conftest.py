import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client(initialize_posts_table) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
