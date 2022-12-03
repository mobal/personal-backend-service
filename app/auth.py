from typing import Optional

import jwt
from aws_lambda_powertools import Logger, Tracer
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from jwt import DecodeError, ExpiredSignatureError
from starlette import status

from app.models.auth import JWTToken
from app.services.cache import CacheService
from app.settings import Settings

tracer = Tracer()


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._logger = Logger()
        self.auto_error = auto_error
        self.cache_service = CacheService()
        self.settings = Settings()

    async def __call__(self, request: Request) -> Optional[JWTToken]:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                if self.auto_error:
                    self._logger.error(f'Invalid authentication token {credentials=}')
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail='Not authenticated',
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
                self._logger.debug(f'Token is not blacklisted {decoded_token=}')
                self.decoded_token = decoded_token
                return True
            self._logger.debug(f'Token blacklisted {decoded_token=}')
        except DecodeError as err:
            self._logger.error(f'Error occurred during token decoding {err=}')
        except ExpiredSignatureError as err:
            self._logger.error(f'Expired signature {err=}')
        return False
