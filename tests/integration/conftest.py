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


@pytest.fixture
def test_client(initialize_posts_table, initialize_rate_limits_table) -> TestClient:
    return TestClient(app, raise_server_exceptions=True)
