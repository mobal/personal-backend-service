import uuid

import pendulum
import pytest

from app.auth import JWTAuth, JWTToken
from app.services.cache import CacheService


@pytest.fixture
def cache_service():
    return CacheService()


@pytest.fixture
def jwt_auth() -> JWTAuth:
    return JWTAuth()


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
