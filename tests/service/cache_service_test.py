import uuid

import pytest
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    async def test_successfully_get_key_value(self, cache_service, config, httpx_mock):
        expired_at = '2022-06-23T20:49:17Z'
        value = 'asd'
        key = str(uuid.uuid4())
        httpx_mock.add_response(url=f'{config.cache_service_base_url}/api/cache/{key}',
                                status_code=status.HTTP_200_OK,
                                json={'key': key, 'value': value, 'expired_at': expired_at})
        result = await cache_service.get(key)
        assert bool(result) is True
        assert key == result.key
        assert expired_at == result.expired_at
        assert value == result.value

    async def test_successfully_get_key_value_with_invalid_id(self, cache_service, config, httpx_mock):
        key = str(uuid.uuid4())
        message = f'The requested value was not found for key={key}'
        httpx_mock.add_response(url=f'{config.cache_service_base_url}/api/cache/{key}',
                                status_code=status.HTTP_404_NOT_FOUND,
                                json={'status': status.HTTP_404_NOT_FOUND, 'id': key, 'message': message})
        result = await cache_service.get(key)
        assert result is None
