import httpx
from aws_lambda_powertools import Logger
from fastapi import status
from httpx import HTTPError, codes

from app import settings
from app.exceptions import CacheServiceException
from app.middlewares import correlation_id


class CacheService:
    def __init__(self):
        self.__logger = Logger(utc=True)

    async def get(self, key: str) -> bool | None:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{settings.cache_service_base_url}/api/cache/{key}"
                self.__logger.debug(f"Get cache for {key=} {url=}")
                response = await client.get(
                    url, headers={"X-Correlation-ID": correlation_id.get()}
                )
            match response.status_code:
                case status.HTTP_200_OK:
                    self.__logger.info(f"{response.json()=}")
                    return True
                case status.HTTP_404_NOT_FOUND:
                    self.__logger.debug(f"Cache was not found for {key=}")
                    return False
                case _:
                    self.__logger.error("Unexpected status code", response=response)
                    raise CacheServiceException(
                        codes.get_reason_phrase(response.status_code)
                    )
        except HTTPError:
            self.__logger.exception("Unexpected error occurred")
            raise CacheServiceException("Internal Server Error")
