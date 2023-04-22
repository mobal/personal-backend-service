from typing import Optional

import jwt
from aws_lambda_powertools import Logger, Tracer
from fastapi import HTTPException, Request
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer as FastAPIHTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jwt import DecodeError, ExpiredSignatureError
from starlette import status

from app.models.auth import JWTToken
from app.services.cache import CacheService
from app.settings import Settings

logger = Logger(utc=True)
tracer = Tracer()

ERROR_MESSAGE_NOT_AUTHENTICATED = 'Not authenticated'


class HTTPBearer(FastAPIHTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auto_error = auto_error

    @tracer.capture_method
    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        authorization = request.headers.get('Authorization')
        if authorization is not None:
            return await self._get_authorization_credentials_from_header(authorization)
        else:
            logger.info(
                'Missing authentication header, attempt to use token query param'
            )
            return await self._get_authorization_credentials_from_token(
                request.query_params.get('token')
            )

    @tracer.capture_method
    async def _get_authorization_credentials_from_header(
        self, authorization: str
    ) -> Optional[HTTPAuthorizationCredentials]:
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            logger.error(f'Missing {authorization=}, {scheme=} or {credentials=}')
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None
        if scheme.lower() != 'bearer':
            logger.error(f'Invalid {scheme=}')
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid authentication credentials',
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

    @tracer.capture_method
    async def _get_authorization_credentials_from_token(
        self, token: Optional[str]
    ) -> Optional[HTTPAuthorizationCredentials]:
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auto_error = auto_error
        self.cache_service = CacheService()
        self.settings = Settings()

    @tracer.capture_method
    async def __call__(self, request: Request) -> Optional[JWTToken]:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                if self.auto_error:
                    logger.error(f'Invalid authentication token {credentials=}')
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                    )
                else:
                    return None
            return self.decoded_token
        else:
            return None

    @tracer.capture_method
    async def _validate_token(self, token: str) -> bool:
        try:
            decoded_token = JWTToken(
                **jwt.decode(token, self.settings.jwt_secret, algorithms='HS256')
            )
            if await self.cache_service.get(f'jti_{decoded_token.jti}') is False:
                logger.debug(f'Token is not blacklisted {decoded_token=}')
                self.decoded_token = decoded_token
                return True
            logger.debug(f'Token blacklisted {decoded_token=}')
        except DecodeError as err:
            logger.error(f'Error occurred during token decoding {err=}')
        except ExpiredSignatureError as err:
            logger.error(f'Expired signature {err=}')
        return False
