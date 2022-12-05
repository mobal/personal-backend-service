import uuid

import pendulum
import pytest
from httpx import Response
from respx import MockRouter
from starlette import status

from app.exceptions import CacheServiceException
from app.services.cache import CacheService
from app.settings import Settings


@pytest.mark.asyncio
class TestCacheService:
    key_value = {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'created_at': pendulum.now().to_iso8601_string(),
        'ttl': pendulum.now().int_timestamp,
    }

    async def test_successfully_get_key_value(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            return_value=Response(status_code=status.HTTP_200_OK, json=self.key_value)
        )
        result = await cache_service.get(self.key_value['key'])
        assert bool(result) is True

    async def test_fail_to_get_key_value_due_to_invalid_id(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        message = f'The requested value was not found for key={self.key_value["key"]}'
        respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_404_NOT_FOUND,
                json={
                    'status': status.HTTP_404_NOT_FOUND,
                    'id': self.key_value['key'],
                    'message': message,
                },
            ),
        )
        result = await cache_service.get(self.key_value['key'])
        assert result is False

    async def test_fail_to_get_key_value_due_to_unexpected_error(self, cache_service: CacheService, settings: Settings,
                                                                 respx_mock: MockRouter):
        message = 'Internal Server Error'
        respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                json={
                    'status': status.HTTP_404_NOT_FOUND,
                    'id': self.key_value['key'],
                    'message': message,
                },
            ),
        )
        with pytest.raises(CacheServiceException) as excinfo:
            await cache_service.get(self.key_value['key'])
        assert excinfo.type.__name__ == CacheServiceException.__name__
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == excinfo.value.status_code
        assert message == excinfo.value.detail
