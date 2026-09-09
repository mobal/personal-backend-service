from typing import Any

from pydantic import BaseModel


class JWTToken(BaseModel):
    exp: int
    iat: int
    aud: str | None = None
    iss: str | None = None
    jti: str
    sub: Any
    user: dict[str, str | None] | None = None
