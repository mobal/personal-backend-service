from typing import Any, List

from pydantic import BaseModel


class User(BaseModel):
    id: str
    roles: List[str]


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str
    jti: str
    sub: Any
