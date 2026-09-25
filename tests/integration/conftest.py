from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api_handler import app


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def override_dependency() -> Generator[dict]:
    overrides: dict = {}

    from app.dependencies import get_jwt_bearer
    from app.models.auth import JWTToken

    bypass = lambda: JWTToken(  # noqa: E731
        exp=9999999999,
        iat=1000000000,
        iss="test",
        jti="test-jti",
        sub="test-user",
        user={"id": "test", "email": "test@test.com", "display_name": "test"},
    )
    overrides[get_jwt_bearer] = bypass

    app.dependency_overrides.update(overrides)
    yield overrides
    app.dependency_overrides.clear()
