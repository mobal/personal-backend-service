import uuid

import pendulum
import pytest
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    @pytest.fixture
    def key_value(self) -> dict:
        return {'key': '601377f5-c8e3-4d0d-b738-304a965b9b2b', 'value': 'cf7f5dbf0f557bb0eea345d79503fe8f',
                'expired_at': pendulum.now().to_iso8601_string()}

    async def test_successfully_get_key_value(self, cache_service, config, httpx_mock, key_value):
        httpx_mock.add_response(url=f'{config.cache_service_base_url}/api/cache/{key_value["key"]}',
                                status_code=status.HTTP_200_OK,
                                json=key_value)
        result = await cache_service.get(key_value['key'])
        assert bool(result) is True
        assert key_value['key'] == result.key
        assert key_value['expired_at'] == result.expired_at
        assert key_value['value'] == result.value

    async def test_successfully_get_key_value_with_invalid_id(self, cache_service, config, httpx_mock, key_value):
        message = f'The requested value was not found for key={key_value["key"]}'
        httpx_mock.add_response(url=f'{config.cache_service_base_url}/api/cache/{key_value["key"]}',
                                status_code=status.HTTP_404_NOT_FOUND,
                                json={'status': status.HTTP_404_NOT_FOUND, 'id': key_value['key'], 'message': message})
        result = await cache_service.get(key_value['key'])
        assert result is None
