import logging
from typing import Optional, Any

import jwt
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from jwt import ExpiredSignatureError, DecodeError
from pydantic import BaseModel
from starlette import status

from app.settings import Settings
from app.services.cache import CacheService
from app.utils import tracer


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str
    jti: str
    sub: Any


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._logger = logging.getLogger()
        self.cache_service = CacheService()
        self.settings = Settings()

    async def __call__(self, request: Request) -> Optional[JWTToken]:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                self._logger.error(
                    f'Invalid authentication token credentials={credentials}'
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid authentication token',
                )
            return self.decoded_token
        else:
            self._logger.error(f'Credentials missing during authentications')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail='Not authenticated'
            )

    @tracer.capture_method
    async def _validate_token(self, token: str) -> bool:
        try:
            decoded_token = jwt.decode(
                token, self.settings.jwt_secret, algorithms='HS256'
            )
        except (DecodeError, ExpiredSignatureError) as error:
            self._logger.error(f'error={error}')
            return False
        if await self.cache_service.get(decoded_token['jti']) is None:
            self.decoded_token = decoded_token
            return True
        return False
