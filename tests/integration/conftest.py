from collections.abc import Generator

import boto3
import pytest
from fastapi.testclient import TestClient

from app.api_handler import app


@pytest.fixture
def initialize_rate_limits_table(aws_default_region: str):
    client = boto3.client("dynamodb", region_name=aws_default_region)
    client.create_table(
        TableName="test-rate-limits",
        KeySchema=[
            {"AttributeName": "client_id", "KeyType": "HASH"},
            {"AttributeName": "endpoint", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "client_id", "AttributeType": "S"},
            {"AttributeName": "endpoint", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield


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
