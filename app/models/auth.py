from typing import Any, List, Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    roles: List[str]


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str]
    jti: str
    sub: Any
