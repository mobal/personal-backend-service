import uuid
from typing import Dict, List, Optional

import jwt
import pendulum
import pytest
from httpx import Response
from respx import MockRouter, Route
from starlette import status
from starlette.testclient import TestClient

from app.auth import JWTBearer
from app.models.post import Post
from app.services.post import PostService


@pytest.mark.asyncio
class TestPostsApi:
    BASE_URL = '/api/v1/posts'
    CACHE_SERVICE_URL = f'{pytest.cache_service_base_url}/api/cache'
    ERROR_MESSAGE_NOT_FOUND = 'The requested post was not found'
    ROLE_POST_CREATE = 'post:create'
    ROLE_POST_DELETE = 'post:delete'
    ROLE_POST_EDIT = 'post:edit'

    @staticmethod
    async def generate_jwt_token(roles: List[str]) -> str:
        iat = pendulum.now()
        exp = iat.add(hours=1)
        return jwt.encode(
            {
                'exp': exp.int_timestamp,
                'iat': iat.int_timestamp,
                'jti': str(uuid.uuid4()),
                'sub': {'id': str(uuid.uuid4()), 'roles': roles},
            },
            pytest.jwt_secret,
        )

    @staticmethod
    async def generate_respx_mock(
        method: str,
        response: Response,
        respx_mock: MockRouter,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Route:
        return respx_mock.route(
            headers=headers, method=method, url__startswith=url
        ).mock(response)

    @pytest.fixture
    def cache_service_response_200(self) -> Response:
        return Response(
            status_code=status.HTTP_200_OK,
            json={
                'key': 'jti_',
                'value': 'asd',
                'createdAt': pendulum.now().to_iso8601_string(),
            },
        )

    @pytest.fixture
    def cache_service_response_403(self) -> Response:
        return Response(
            status_code=status.HTTP_403_FORBIDDEN,
            json={
                'status': status.HTTP_403_FORBIDDEN,
                'id': str(uuid.uuid4()),
                'message': JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED,
            },
        )

    @pytest.fixture
    def cache_service_response_404(self) -> Response:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                'status': status.HTTP_404_NOT_FOUND,
                'id': str(uuid.uuid4()),
                'message': 'Not found',
            },
        )

    @pytest.fixture
    def test_client(self, initialize_posts_table) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_successfully_get_all_posts(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.get(TestPostsApi.BASE_URL)
        assert response.status_code == status.HTTP_200_OK
        json = response.json()
        assert len(json) == 1
        post = json[0]
        assert post_model.id == post['id']
        assert post_model.title == post['title']
        assert post_model.published_at == post['publishedAt']
        assert post_model.meta == post['meta']

    async def test_fail_to_get_post_by_uuid_due_to_not_found(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.get(
            f'{TestPostsApi.BASE_URL}/653000ce-4b15-4242-a07d-fd8eed656d36'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        json = response.json()
        assert json['status'] == status.HTTP_404_NOT_FOUND
        assert json['message'] == TestPostsApi.ERROR_MESSAGE_NOT_FOUND

    async def test_successfully_get_post_by_uuid(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.get(f'{TestPostsApi.BASE_URL}/{post_model.id}')
        assert response.status_code == status.HTTP_200_OK
        post = response.json()
        assert post['id'] == post_model.id

    async def test_successfully_get_archive(self, test_client: TestClient):
        response = test_client.get(f'{TestPostsApi.BASE_URL}/archive')
        assert response.status_code == status.HTTP_200_OK
        archive = response.json()
        date = pendulum.now().format('YYYY-MM')
        assert archive.get(date)
        assert archive[date] == 1

    async def test_successfully_get_post_by_date_and_slug(
        self, post_model: Post, test_client: TestClient
    ):
        now = pendulum.now()
        response = test_client.get(
            f'{TestPostsApi.BASE_URL}/{now.year}/{now.month}/{now.day}/{post_model.slug}'
        )
        assert response.status_code == status.HTTP_200_OK
        post = response.json()
        assert post['id'] == post_model.id

    async def test_fail_to_get_post_by_date_and_slug_due_to_not_found(
        self, test_client: TestClient
    ):
        response = test_client.get(f'{TestPostsApi.BASE_URL}/1970/01/01/slug')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        json = response.json()
        assert json['status'] == status.HTTP_404_NOT_FOUND
        assert json['message'] == TestPostsApi.ERROR_MESSAGE_NOT_FOUND

    async def test_fail_to_delete_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        result = response.json()
        assert result['status'] == status.HTTP_404_NOT_FOUND
        assert result['message'] == PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_delete_post_due_to_unauthorized(
        self,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        response = test_client.delete(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer '},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_delete_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_delete_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token(['post:create'])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        result = response.json()
        assert result['status'] == status.HTTP_401_UNAUTHORIZED
        assert result['message'] == 'Not authorized'
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_successfully_delete_post(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{TestPostsApi.BASE_URL}/{post_model.id}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_unauthorized(
        self,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        response = test_client.post(
            TestPostsApi.BASE_URL,
            headers={'Authorization': f'Bearer '},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_create_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_CREATE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            TestPostsApi.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            TestPostsApi.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        result = response.json()
        assert result['status'] == status.HTTP_401_UNAUTHORIZED
        assert result['message'] == 'Not authorized'
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_successfully_create_post(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_CREATE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            TestPostsApi.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers['Location']
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_EDIT])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        result = response.json()
        assert result['status'] == status.HTTP_404_NOT_FOUND
        assert result['message'] == PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_unauthorized(
        self,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        response = test_client.put(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer '},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_update_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['message'] == JWTBearer.ERROR_MESSAGE_NOT_AUTHENTICATED
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_DELETE])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{TestPostsApi.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        result = response.json()
        assert result['status'] == status.HTTP_401_UNAUTHORIZED
        assert result['message'] == 'Not authorized'
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_successfully_update_post(
        self,
        cache_service_response_404: Response,
        post_model: Post,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self.generate_jwt_token([TestPostsApi.ROLE_POST_EDIT])
        cache_service_mock = await self.generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            TestPostsApi.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{TestPostsApi.BASE_URL}/{post_model.id}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=post_model.dict(),
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1