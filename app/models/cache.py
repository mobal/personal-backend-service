from fastapi_camelcase import CamelModel


class Cache(CamelModel):
    key: str
    value: str
    expired_at: str
