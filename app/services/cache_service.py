import httpx
from aws_lambda_powertools import Logger
from httpx import HTTPError
from starlette import status

from app import settings
from app.exceptions import CacheServiceException
from app.middlewares import correlation_id


class CacheService:
    def __init__(self):
        self._logger = Logger(utc=True)

    async def get(self, key: str) -> bool | None:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{settings.cache_service_base_url}/api/cache/{key}"
                self._logger.debug(f"Get cache for {key=} {url=}")
                response = await client.get(
                    url, headers={"X-Correlation-ID": correlation_id.get()}
                )
            match response.status_code:
                case status.HTTP_200_OK:
                    self._logger.info(f"{response.json()=}")
                    return True
                case status.HTTP_404_NOT_FOUND:
                    self._logger.debug(f"Cache was not found for {key=}")
                    return False
                case _:
                    raise CacheServiceException(response.json()["message"])
        except HTTPError as exc:
            self._logger.exception("Unexpected error occurred", exc_info=exc)
            raise CacheServiceException(exc)
