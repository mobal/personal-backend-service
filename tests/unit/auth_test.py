from unittest.mock import MagicMock

import jwt
import pendulum
import pytest
from fastapi import HTTPException
from starlette import status

from app.auth import JWTAuth, JWTToken

INVALID_AUTHENTICATION_TOKEN = 'Invalid authentication token'
NOT_AUTHENTICATED = 'Not authenticated'


@pytest.fixture
def jwt_auth() -> JWTAuth:
    return JWTAuth()


@pytest.fixture
def jwt_token() -> JWTToken:
    now = pendulum.now()
    return JWTToken(exp=now.add(hours=1).int_timestamp, iat=now.int_timestamp, iss='https://netcode.hu',
                    jti='7a93ffe1-34b8-42d1-b3da-90d5273da171', sub={'id': 'b5d21631-1c27-4e00-99ad-9de532daaca2',
                                                                     'email': 'info@netcode.hu', 'display_name': 'root',
                                                                     'roles': ['root'],
                                                                     'created_at': now.to_iso8601_string(),
                                                                     'deleted_at': None, 'updated_at': None})


def _encode_jwt_token(jwt_token: JWTToken, key: str) -> str:
    return jwt.encode(jwt_token.dict(), key)


@pytest.fixture
def empty_request(mocker) -> MagicMock:
    request = mocker.patch('starlette.requests.Request')
    request.headers = {}
    return request


@pytest.fixture
def valid_request(config, empty_request, jwt_token) -> MagicMock:
    token = _encode_jwt_token(jwt_token, config.jwt_secret)
    empty_request.headers = {'Authorization': f'Bearer {token}'}
    return empty_request


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_authorization_header_is_empty(empty_request, jwt_auth, jwt_token):
    empty_request.headers = {'Authorization': ''}
    with pytest.raises(HTTPException) as excinfo:
        await jwt_auth(empty_request)
    assert NOT_AUTHENTICATED == excinfo.value.detail
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_authorization_header_is_missing(empty_request, jwt_auth, jwt_token):
    with pytest.raises(HTTPException) as excinfo:
        await jwt_auth(empty_request)
    assert NOT_AUTHENTICATED == excinfo.value.detail
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_bearer_token_is_invalid(empty_request, jwt_auth, jwt_token):
    empty_request.headers = {'Authorization': 'Bearer asdf'}
    with pytest.raises(HTTPException) as excinfo:
        await jwt_auth(empty_request)
    assert INVALID_AUTHENTICATION_TOKEN == excinfo.value.detail
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_bearer_token_is_missing(empty_request, jwt_auth, jwt_token):
    empty_request.headers = {'Authorization': 'Bearer '}
    with pytest.raises(HTTPException) as excinfo:
        await jwt_auth(empty_request)
    assert NOT_AUTHENTICATED == excinfo.value.detail
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_blacklisted_token(mocker, cache_service, jwt_auth, jwt_token,
                                                                  valid_request):
    mocker.patch('app.services.cache.CacheService.get', return_value=jwt_token.jti)
    with (pytest.raises(HTTPException)) as excinfo:
        await jwt_auth(valid_request)
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
    assert INVALID_AUTHENTICATION_TOKEN == excinfo.value.detail
    cache_service.get.assert_called_once_with(jwt_token.jti)


@pytest.mark.asyncio
async def test_fail_to_authorize_request_due_to_missing_credentials(empty_request):
    jwt_auth = JWTAuth(auto_error=False)
    with (pytest.raises(HTTPException)) as excinfo:
        await jwt_auth(empty_request)
    assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
    assert NOT_AUTHENTICATED == excinfo.value.detail


@pytest.mark.asyncio
async def test_successfully_authorize_request(mocker, cache_service, jwt_auth, jwt_token, valid_request):
    mocker.patch('app.services.cache.CacheService.get', return_value=None)
    result = await jwt_auth(valid_request)
    assert jwt_token.dict() == result
    cache_service.get.assert_called_once_with(jwt_token.jti)
