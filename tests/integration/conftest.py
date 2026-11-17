import pytest
from fastapi.testclient import TestClient

from app.api_handler import app


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)
