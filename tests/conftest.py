import uuid

import boto3
import pendulum
import pytest
from moto import mock_dynamodb

from app.auth import JWTToken
from app.config import Configuration
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
    now = pendulum.now()
    return JWTToken(
        exp=now.add(
            hours=1).int_timestamp,
        iat=now.int_timestamp,
        iss='https://netcode.hu',
        jti=str(
            uuid.uuid4()),
        sub={
            'id': str(
                uuid.uuid4()),
            'email': 'info@netcode.hu',
            'display_name': 'root',
            'roles': ['root'],
            'created_at': now.to_iso8601_string(),
            'deleted_at': None,
            'updated_at': None})
