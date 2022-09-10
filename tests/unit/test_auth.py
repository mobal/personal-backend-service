from unittest.mock import Mock

import jwt
import pytest
from fastapi import HTTPException
from starlette import status
from starlette.requests import Request

from app.auth import JWTBearer
from app.models.auth import JWTToken
from app.services.cache import CacheService

NOT_AUTHENTICATED = 'Not authenticated'


@pytest.fixture
def empty_request() -> Mock:
    request = Mock()
    request.headers = {}
    return request


@pytest.fixture
def valid_request(settings, empty_request: Mock, jwt_token: JWTToken) -> Mock:
    empty_request.headers = {
        'Authorization': f'Bearer {jwt.encode(jwt_token.dict(), settings.jwt_secret)}'
    }
    return empty_request


@pytest.mark.asyncio
class TestJWTAuth:
    async def test_fail_to_authorize_request_due_to_authorization_header_is_empty(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {'Authorization': ''}
        with pytest.raises(HTTPException) as excinfo:
            await jwt_bearer(empty_request)
        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    async def test_fail_to_authorize_request_due_to_authorization_header_is_missing(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        with pytest.raises(HTTPException) as excinfo:
            await jwt_bearer(empty_request)
        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    async def test_fail_to_authorize_request_due_to_bearer_token_is_invalid(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {'Authorization': 'Bearer asdf'}
        with pytest.raises(HTTPException) as excinfo:
            await jwt_bearer(empty_request)
        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    async def test_fail_to_authorize_request_due_to_bearer_token_is_invalid_with_auto_error_false(
        self, empty_request: Mock
    ):
        empty_request.headers = {'Authorization': 'Bearer asdf'}
        jwt_bearer = JWTBearer(auto_error=False)
        result = await jwt_bearer(empty_request)
        assert result is None

    async def test_fail_to_authorize_request_due_to_bearer_token_is_missing(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {'Authorization': 'Bearer '}
        with pytest.raises(HTTPException) as excinfo:
            await jwt_bearer(empty_request)
        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    async def test_fail_to_authorize_request_due_to_blacklisted_token(
        self,
        mocker,
        cache_service: CacheService,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        valid_request: Request,
    ):
        mocker.patch('app.services.cache.CacheService.get', return_value=jwt_token.jti)
        with (pytest.raises(HTTPException)) as excinfo:
            await jwt_bearer(valid_request)
        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
        cache_service.get.assert_called_once_with(f'jti_{jwt_token.jti}')

    async def test_fail_to_authorize_request_due_to_missing_credentials(
        self, empty_request: Mock
    ):
        jwt_bearer = JWTBearer()
        with (pytest.raises(HTTPException)) as excinfo:
            await jwt_bearer(empty_request)
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
        assert NOT_AUTHENTICATED == excinfo.value.detail

    async def test_fail_to_authorize_request_due_to_missing_credentials_with_auto_error_false(
        self, empty_request: Mock
    ):
        jwt_bearer = JWTBearer(auto_error=False)
        result = await jwt_bearer(empty_request)
        assert result is None

    async def test_successfully_authorize_request(
        self,
        mocker,
        cache_service: CacheService,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        valid_request: Request,
    ):
        mocker.patch('app.services.cache.CacheService.get', return_value=False)
        result = await jwt_bearer(valid_request)
        assert jwt_token.dict() == result
        cache_service.get.assert_called_once_with(f'jti_{jwt_token.jti}')
