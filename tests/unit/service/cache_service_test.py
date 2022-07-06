import pendulum
import pytest
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    KEY_VALUE = {
        'key': '601377f5-c8e3-4d0d-b738-304a965b9b2b',
        'value': 'cf7f5dbf0f557bb0eea345d79503fe8f',
        'expired_at': pendulum.now().to_iso8601_string()}

    async def test_successfully_get_key_value(self, cache_service, config, httpx_mock):
        httpx_mock.add_response(
            url=f'{config.cache_service_base_url}/api/cache/{self.KEY_VALUE["key"]}',
            status_code=status.HTTP_200_OK,
            json=self.KEY_VALUE)
        result = await cache_service.get(self.KEY_VALUE['key'])
        assert bool(result) is True
        assert self.KEY_VALUE['key'] == result.key
        assert self.KEY_VALUE['expired_at'] == result.expired_at
        assert self.KEY_VALUE['value'] == result.value

    async def test_successfully_get_key_value_with_invalid_id(self, cache_service, config, httpx_mock):
        message = f'The requested value was not found for key={self.KEY_VALUE["key"]}'
        httpx_mock.add_response(
            url=f'{config.cache_service_base_url}/api/cache/{self.KEY_VALUE["key"]}',
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                'status': status.HTTP_404_NOT_FOUND,
                'id': self.KEY_VALUE['key'],
                'message': message})
        result = await cache_service.get(self.KEY_VALUE['key'])
        assert result is None
