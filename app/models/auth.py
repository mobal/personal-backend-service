from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Role(StrEnum):
    ATTACHMENT_CREATE = "attachment:create"
    POST_CREATE = "post:create"
    POST_DELETE = "post:delete"
    POST_UPDATE = "post:edit"


class User(BaseModel):
    roles: list[Role]


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str | None = None
    jti: str
    sub: Any
