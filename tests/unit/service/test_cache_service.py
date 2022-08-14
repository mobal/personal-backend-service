import uuid
import pendulum
import pytest
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    key_value = {
        'key': str(uuid.uuid4()),
        'value': 'Some random value',
        'expired_at': pendulum.now().to_iso8601_string(),
    }

    async def test_successfully_get_key_value(
        self, cache_service, settings, httpx_mock
    ):
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}',
            status_code=status.HTTP_200_OK,
            json=self.key_value,
        )
        result = await cache_service.get(self.key_value['key'])
        assert bool(result) is True
        assert self.key_value['key'] == result.key
        assert self.key_value['expired_at'] == result.expired_at
        assert self.key_value['value'] == result.value

    async def test_successfully_get_key_value_with_invalid_id(
        self, cache_service, settings, httpx_mock
    ):
        message = f'The requested value was not found for key={self.key_value["key"]}'
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}',
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                'status': status.HTTP_404_NOT_FOUND,
                'id': self.key_value['key'],
                'message': message,
            },
        )
        result = await cache_service.get(self.key_value['key'])
        assert result is None
