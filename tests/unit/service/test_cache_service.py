import uuid

import pendulum
import pytest
from fastapi import status
from httpx import ConnectError, Response
from respx import MockRouter

from app.exceptions import CacheServiceException
from app.middlewares import correlation_id
from app.services.cache_service import CacheService
from app.settings import Settings


@pytest.mark.asyncio
class TestCacheService:
    key_value = {
        "key": str(uuid.uuid4()),
        "value": "Some random value",
        "created_at": pendulum.now().to_iso8601_string(),
        "ttl": pendulum.now().int_timestamp,
    }

    @pytest.fixture(autouse=True)
    def setup_function(self):
        correlation_id.set(str(uuid.uuid4()))

    async def test_successfully_get_key_value(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        cache_service_mock = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            return_value=Response(status_code=status.HTTP_200_OK, json=self.key_value)
        )

        result = await cache_service.get(self.key_value["key"])

        assert result is True
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_get_key_value_due_to_invalid_id(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        message = f'The requested value was not found for key={self.key_value["key"]}'
        cache_service_mock = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_404_NOT_FOUND,
                json={
                    "status": status.HTTP_404_NOT_FOUND,
                    "id": self.key_value["key"],
                    "message": message,
                },
            ),
        )

        result = await cache_service.get(self.key_value["key"])

        assert result is False
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_get_key_value_due_to_unexpected_error(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        message = "Internal Server Error"
        cache_service_mock = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                json={
                    "status": status.HTTP_404_NOT_FOUND,
                    "id": self.key_value["key"],
                    "message": message,
                },
            ),
        )

        with pytest.raises(CacheServiceException) as exc_info:
            await cache_service.get(self.key_value["key"])

        assert exc_info.type == CacheServiceException
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == message
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_get_key_value_due_to_connection_error(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        cache_service_mock = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        )
        cache_service_mock.side_effect = ConnectError(
            "[Errno 16] Device or resource busy"
        )

        with pytest.raises(CacheServiceException) as exc_info:
            await cache_service.get(self.key_value["key"])

        assert exc_info.type == CacheServiceException
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1
