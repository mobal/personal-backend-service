import random
import uuid
from typing import Dict, List, Optional

import jwt
import pendulum
import pytest
from httpx import Response
from respx import MockRouter, Route
from starlette import status
from starlette.testclient import TestClient

from app.models.post import Post
from app.schemas.post import CreatePost


@pytest.mark.asyncio
class TestPostsApi:
    BASE_URL = '/api/v1/posts'
    CACHE_SERVICE_URL = f'{pytest.cache_service_base_url}/api/cache'
    ERROR_MESSAGE_INTERNAL_SERVER_ERROR = 'Internal server error'
    ERROR_MESSAGE_NOT_AUTHENTICATED = 'Not authenticated'
    ERROR_MESSAGE_NOT_AUTHORIZED = 'Not authorized'
    ERROR_MESSAGE_NOT_FOUND = 'The requested post was not found'
    ROLE_POST_CREATE = 'post:create'
    ROLE_POST_DELETE = 'post:delete'
    ROLE_POST_EDIT = 'post:edit'

    async def _assert_response(
        self,
        cache_service_mock: Route,
        message: str,
        status_code: int,
        response: Response,
    ):
        assert response.status_code == status_code
        result = response.json()
        assert result['status'] == status_code
        assert result['id']
        assert result['message'] == message
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def _generate_jwt_token(self, role: str, exp: int = 1) -> str:
        iat = pendulum.now()
        exp = iat.add(hours=exp)
        return jwt.encode(
            {
                'exp': exp.int_timestamp,
                'iat': iat.int_timestamp,
                'jti': str(uuid.uuid4()),
                'sub': {'id': str(uuid.uuid4()), 'roles': [role]},
            },
            pytest.jwt_secret,
        )

    async def _generate_respx_mock(
        self,
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
                'message': self.ERROR_MESSAGE_NOT_AUTHENTICATED,
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
    def cache_service_response_500(self) -> Response:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            json={
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'id': str(uuid.uuid4()),
                'message': 'Internal server error',
            },
        )

    @pytest.fixture
    def create_post(self, make_post) -> CreatePost:
        post = make_post()
        return CreatePost(
            author=post.author,
            title=post.title,
            content=post.content,
            tags=post.tags,
            meta=post.meta.dict(),
            published_at=post.published_at,
        )

    @pytest.fixture
    def test_client(self, initialize_posts_table) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_successfully_get_posts(
        self, posts: List[Post], test_client: TestClient
    ):
        response = test_client.get(self.BASE_URL)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()['data']
        assert len(result) == len(posts)

    async def test_fail_to_get_post_by_uuid_due_to_not_found(
        self, posts: List[Post], test_client: TestClient
    ):
        response = test_client.get(
            f'{self.BASE_URL}/653000ce-4b15-4242-a07d-fd8eed656d36'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        result = response.json()
        assert result['status'] == status.HTTP_404_NOT_FOUND
        assert result['id']
        assert result['message'] == self.ERROR_MESSAGE_NOT_FOUND

    async def test_successfully_get_post_by_uuid(
        self, posts: List[Post], test_client: TestClient
    ):
        response = test_client.get(f'{self.BASE_URL}/{posts[0].id}')
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result['id'] == posts[0].id

    async def test_successfully_get_archive(
        self, posts: List[Post], test_client: TestClient
    ):
        response = test_client.get(f'{self.BASE_URL}/archive')
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        date = pendulum.now().format('YYYY-MM')
        assert result[date] == len(posts)

    async def test_successfully_get_post_by_date_and_slug(
        self, posts: List[Post], test_client: TestClient
    ):
        now = pendulum.now()
        response = test_client.get(
            f'{self.BASE_URL}/{now.year}/{now.month}/{now.day}/{posts[0].slug}'
        )
        assert response.status_code == status.HTTP_200_OK
        post = response.json()
        assert post['id'] == posts[0].id

    async def test_fail_to_get_post_by_date_and_slug_due_to_not_found(
        self, test_client: TestClient
    ):
        response = test_client.get(
            f'{self.BASE_URL}/{random.randint(1970, 2999)}/{random.randint(3, 12)}/{random.randint(1, 30)}/slug'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        result = response.json()
        assert result['status'] == status.HTTP_404_NOT_FOUND
        assert result['id']
        assert result['message'] == self.ERROR_MESSAGE_NOT_FOUND

    async def test_fail_to_delete_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_FOUND,
            status.HTTP_404_NOT_FOUND,
            response,
        )

    async def test_fail_to_delete_post_due_to_unauthorized(
        self, test_client: TestClient
    ):
        response = test_client.delete(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer '},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['id']
        assert result['message'] == self.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_delete_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_delete_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_delete_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_500,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_delete_post(
        self,
        cache_service_response_404: Response,
        posts: List[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.delete(
            f'{self.BASE_URL}/{posts[0].id}',
            headers={'Authorization': f'Bearer {jwt_token}'},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_bad_request(
        self,
        cache_service_response_404,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL, headers={'Authorization': f'Bearer {jwt_token}'}, json={}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        result = response.json()
        assert result['status'] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result['id']
        assert result['message']
        assert result['errors']
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_unauthorized(
        self,
        create_post: CreatePost,
        test_client: TestClient,
    ):
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer '},
            json=create_post.dict(by_alias=True),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['id']
        assert result['message'] == self.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_create_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_create_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_create_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_500,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_create_post(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers['Location']
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_create_post_due_to_already_exists_by_title(
        self,
        cache_service_response_404: Response,
        posts: List[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_CREATE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.post(
            self.BASE_URL,
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=CreatePost(**posts[0].dict()).dict(by_alias=True),
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_not_found(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_EDIT)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_FOUND,
            status.HTTP_404_NOT_FOUND,
            response,
        )

    async def test_fail_to_update_post_due_to_bad_request(
        self,
        cache_service_response_404,
        posts: List[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_EDIT)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{posts[0].id}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json={
                'author': 'a',
                'title': 't',
                'content': 'c',
                'tags': [],
                'published_at': 0,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        result = response.json()
        assert result['status'] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result['id']
        assert result['message']
        assert result['errors']
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_fail_to_update_post_due_to_unauthorized(
        self,
        create_post: CreatePost,
        test_client: TestClient,
    ):
        response = test_client.put(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer '},
            json=create_post.dict(by_alias=True),
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        result = response.json()
        assert result['status'] == status.HTTP_403_FORBIDDEN
        assert result['id']
        assert result['message'] == self.ERROR_MESSAGE_NOT_AUTHENTICATED

    async def test_fail_to_update_post_due_to_blacklisted_jwt_token(
        self,
        cache_service_response_200: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_200,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHENTICATED,
            status.HTTP_403_FORBIDDEN,
            response,
        )

    async def test_fail_to_update_post_due_to_missing_privileges(
        self,
        cache_service_response_404: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_NOT_AUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
            response,
        )

    async def test_fail_to_update_post_due_to_unexpected_cache_service_exception(
        self,
        cache_service_response_500: Response,
        create_post: CreatePost,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_DELETE)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_500,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{str(uuid.uuid4())}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=create_post.dict(by_alias=True),
        )
        await self._assert_response(
            cache_service_mock,
            self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            response,
        )

    async def test_successfully_update_post(
        self,
        cache_service_response_404: Response,
        posts: List[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token(self.ROLE_POST_EDIT)
        cache_service_mock = await self._generate_respx_mock(
            'GET',
            cache_service_response_404,
            respx_mock,
            self.CACHE_SERVICE_URL,
        )
        response = test_client.put(
            f'{self.BASE_URL}/{posts[0].id}',
            headers={'Authorization': f'Bearer {jwt_token}'},
            json=posts[0].dict(),
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1
