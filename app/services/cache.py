from typing import Optional

import httpx
from aws_lambda_powertools import Logger, Tracer
from starlette import status

from app.exceptions import CacheServiceException
from app.middlewares import correlation_id
from app.settings import Settings

tracer = Tracer()


class CacheService:
    def __init__(self):
        self._logger = Logger(utc=True)
        self._settings = Settings()

    @tracer.capture_method
    async def get(self, key: str) -> Optional[bool]:
        async with httpx.AsyncClient() as client:
            url = f'{self._settings.cache_service_base_url}/api/cache/{key}'
            self._logger.debug(f'Get cache for {key=} {url=}')
            response = await client.get(
                url, headers={'X-Correlation-ID': correlation_id.get()}
            )
        if response.is_success:
            self._logger.info(f'{response.json()=}')
            return True
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            self._logger.debug(f'Cache was not found for {key=}')
            return False
        self._logger.error(f'Unexpected error {response=}')
        raise CacheServiceException(response.json()['message'])
