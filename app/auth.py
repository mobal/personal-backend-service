import jwt
import logging

import pendulum
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
from jwt import InvalidSignatureError
from pydantic import BaseModel
from starlette import status

from app.config import Configuration


class JWTToken(BaseModel):
    sub: str
    exp: int
    iat: int


class JWTAuth(HTTPBearer):
    config = Configuration()
    logger = logging.getLogger(__name__)

    async def __call__(self, request: Request):
        credentials = await super(JWTAuth, self).__call__(request)
        if credentials:
            if credentials.scheme != 'Bearer':
                self.logger.error(f'Invalid authentication scheme credentials={credentials}')
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid authentication scheme')
            if not self.validate_token(credentials.credentials):
                self.logger.error(f'Invalid authentication token credentials={credentials}')
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid authentication token')
            return credentials.credentials
        else:
            self.logger.error(f'Credentials missing during authentications')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def validate_token(self, token: str) -> bool:
        try:
            decoded_token = jwt.decode(token, self.config.jwt_secret, algorithms='HS256')
        except InvalidSignatureError as error:
            self.logger.error(f'Failed to validate JWT token signature error={error}')
            return False
        return True if pendulum.from_timestamp(decoded_token['exp']) > pendulum.now() else False
