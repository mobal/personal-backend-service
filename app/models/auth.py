from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel


class Role(str, Enum):
    POST_CREATE = 'post:create'
    POST_DELETE = 'post:delete'
    POST_UPDATE = 'post:edit'


class User(BaseModel):
    id: str
    roles: List[Role]


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str]
    jti: str
    sub: Any
