import uuid

import pendulum
import pytest
from httpx import Response
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    key_value = {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'created_at': pendulum.now().to_iso8601_string(),
        'ttl': pendulum.now().int_timestamp,
    }

    async def test_successfully_get_key_value(
        self, cache_service, settings, respx_mock
    ):
        respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            return_value=Response(status_code=status.HTTP_200_OK, json=self.key_value)
        )
        result = await cache_service.get(self.key_value['key'])
        assert bool(result) is True
        assert self.key_value['key'] == result.key
        assert self.key_value['created_at'] == result.created_at
        assert self.key_value['value'] == result.value
        assert self.key_value['ttl'] == result.ttl

    async def test_successfully_get_key_value_with_invalid_id(
        self, cache_service, settings, respx_mock
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
        assert result is None
