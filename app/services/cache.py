import logging
from typing import Optional

import httpx
from starlette import status

from app.config import Configuration
from app.models.cache import Cache


class CacheService:
    def __init__(self):
        self.logger = logging.getLogger()
        self.config = Configuration()

    async def get(self, key: str) -> Optional[Cache]:
        async with httpx.AsyncClient() as client:
            res = await client.get(f'{self.config.cache_service_base_url}/api/cache/{key}')
        if res.status_code != status.HTTP_200_OK:
            return None
        return None