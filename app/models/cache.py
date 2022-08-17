from typing import Any

from fastapi_camelcase import CamelModel


class Cache(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int
