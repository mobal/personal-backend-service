import boto3
import pytest
from moto import mock_dynamodb
from starlette.testclient import TestClient

from app.auth import JWTToken
from app.config import Configuration
from app.main import app
from app.services.cache import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def config() -> Configuration:
    return Configuration()


@pytest.fixture
def dynamodb_client():
    with mock_dynamodb():
        yield boto3.resource('dynamodb')


@pytest.fixture
def jwt_token() -> JWTToken:
    return JWTToken(exp=1655925518, iat=1655921918, iss='https://netcode.hu',
                    jti='7a93ffe1-34b8-42d1-b3da-90d5273da171', sub={'id': 'b5d21631-1c27-4e00-99ad-9de532daaca2',
                                                                     'email': 'info@netcode.hu', 'display_name': 'root',
                                                                     'roles': ['root'],
                                                                     'created_at': '2022-06-23T20:49:17Z',
                                                                     'deleted_at': None, 'updated_at': None})


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
