import logging
from typing import Optional

import httpx
from starlette import status

from app.settings import Settings
from app.models.cache import Cache


class CacheService:
    def __init__(self):
        self._logger = logging.getLogger()
        self.settings = Settings()

    async def get(self, key: str) -> Optional[Cache]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.settings.cache_service_base_url}/api/cache/{key}'
            )
        if response.status_code == status.HTTP_200_OK:
            return Cache.parse_obj(response.json())
        return None
