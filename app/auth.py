import logging
from typing import Optional, Any

import jwt
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from fastapi_camelcase import CamelModel
from jwt import ExpiredSignatureError, DecodeError
from pydantic import EmailStr, BaseModel
from starlette import status

from app.settings import Settings
from app.services.cache import CacheService


class User(CamelModel):
    id: str
    email: EmailStr
    display_name: str
    roles: Optional[list[str]]
    created_at: str
    deleted_at: Optional[str]
    updated_at: Optional[str]


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str
    jti: str
    sub: Any


class JWTAuth(HTTPBearer):
    cache_service = CacheService()
    config = Settings()
    logger = logging.getLogger()

    async def __call__(self, request: Request) -> Optional[JWTToken]:
        credentials = await super(JWTAuth, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                self.logger.error(
                    f'Invalid authentication token credentials={credentials}')
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid authentication token')
            return self.decoded_token
        else:
            self.logger.error(f'Credentials missing during authentications')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Not authenticated')

    async def _validate_token(self, token: str) -> bool:
        try:
            decoded_token = jwt.decode(
                token, self.config.jwt_secret, algorithms='HS256')
        except (DecodeError, ExpiredSignatureError) as error:
            self.logger.error(f'error={error}')
            return False
        if await self.cache_service.get(decoded_token['jti']) is None:
            self.decoded_token = decoded_token
            return True
        return False
