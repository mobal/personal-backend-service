import copy
from unittest.mock import ANY

import jwt
import pendulum
import pytest
from botocore.exceptions import ClientError
from starlette import status
from starlette.testclient import TestClient

from app.exceptions import PostNotFoundException
from app.middlewares import correlation_id
from app.models.auth import JWTToken
from app.models.post import Post
from app.models.response import Post as PostResponse
from app.schemas.post import CreatePost
from app.services.cache import CacheService
from app.services.post import PostService
from app.settings import Settings


@pytest.mark.asyncio
class TestApp:
    NOT_AUTHENTICATED = 'Not authenticated'
    NOT_AUTHORIZED = 'Not authorized'
    POST_SERVICE_UPDATE_POST = 'app.services.post.PostService.update_post'
    X_CORRELATION_ID = 'X-Correlation-ID'

    @pytest.fixture
    def test_client_ex(
        self, jwt_token: JWTToken, test_client: TestClient
    ) -> TestClient:
        from app.api.v1.routes.posts import jwt_bearer

        test_client.app.dependency_overrides[jwt_bearer] = lambda: jwt_token
        return test_client

    @pytest.fixture
    def test_client_ex_without_roles(
        self, jwt_token_without_roles: JWTToken, test_client: TestClient
    ) -> TestClient:
        from app.api.v1.routes.posts import jwt_bearer

        test_client.app.dependency_overrides[
            jwt_bearer
        ] = lambda: jwt_token_without_roles
        return test_client

    @pytest.fixture(autouse=True)
    def clear_dependency_overrides(self, test_client: TestClient):
        test_client.app.dependency_overrides = {}

    @pytest.fixture
    def json_body(self, post_dict: dict) -> dict:
        return {
            'author': post_dict['author'],
            'title': post_dict['title'],
            'content': post_dict['content'],
            'tags': post_dict['tags'],
            'meta': post_dict['meta'],
        }

    @pytest.fixture
    def post_service(self) -> PostService:
        return PostService()

    @pytest.fixture
    def test_client(self) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_fail_to_create_post_due_to_invalid_body(
        self, test_client_ex: TestClient
    ):
        response = test_client_ex.post(f'/api/v1/posts', json=None)
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 4

    async def test_fail_to_create_post_due_to_empty_authorization_header(
        self, json_body: dict, test_client: TestClient
    ):
        response = test_client.post(
            f'/api/v1/posts', headers={'Authorization': None}, json=json_body
        )
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 3

    async def test_fail_to_create_post_due_to_missing_authorization_header(
        self, json_body: dict, test_client: TestClient
    ):
        response = test_client.post(f'/api/v1/posts', json=json_body)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 3

    async def test_fail_to_create_post_due_to_unauthorized(
        self, json_body: dict, test_client_ex_without_roles: TestClient
    ):
        response = test_client_ex_without_roles.post(f'/api/v1/posts', json=json_body)
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 3

    async def test_successfully_create_post(
        self,
        mocker,
        json_body: dict,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        mocker.patch(
            'app.services.post.PostService.create_post', return_value=post_model
        )
        response = test_client_ex.post(f'/api/v1/posts', json=json_body)
        assert status.HTTP_201_CREATED == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert 'location' in response.headers
        post_service.create_post.assert_called_once_with(
            CreatePost.parse_obj(json_body)
        )

    async def test_successfully_get_post(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        mocker.patch('app.services.post.PostService.get_post', return_value=post_model)
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_200_OK == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert post_model == Post.parse_obj(response.json())
        post_service.get_post.assert_called_once_with(post_model.id)

    async def test_fail_to_get_post_due_to_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            'app.services.post.PostService.get_post',
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert error_message == response.json()['message']
        json = response.json()
        assert len(json) == 3
        post_service.get_post.assert_called_once_with(post_model.id)

    async def test_successfully_get_all_posts(
        self,
        mocker,
        post_fields: str,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        mocker.patch(
            'app.services.post.PostService.get_all_posts', return_value=[post_model]
        )
        response = test_client.get(f'/api/v1/posts?fields={post_fields}')
        assert status.HTTP_200_OK == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        json = response.json()
        assert len(json) == 1
        assert post_model.id == json[0]['id']
        post_service.get_all_posts.assert_called_once()

    async def test_fail_to_delete_post_due_to_post_not_found_exception(
        self,
        mocker,
        json_body: dict,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            'app.services.post.PostService.delete_post',
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = test_client_ex.delete(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert error_message == response.json()['message']
        assert len(response.json()) == 3
        post_service.delete_post.assert_called_once_with(post_model.id)

    async def test_successfully_delete_post(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        mocker.patch('app.services.post.PostService.delete_post', return_value=None)
        response = test_client_ex.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_204_NO_CONTENT == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        post_service.delete_post.assert_called_once_with(post_model.id)

    async def test_fail_to_delete_post_due_to_empty_authorization_header(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.delete(
            f'/api/v1/posts/{post_model.id}', headers={'Authorization': None}
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_delete_post_due_to_missing_authorization_header(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_delete_post_due_to_unauthorized(
        self, post_model: Post, test_client_ex_without_roles: TestClient
    ):
        response = test_client_ex_without_roles.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_missing_authorization_header(
        self, post_model: Post, test_client: TestClient
    ):
        response = test_client.put(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_validation_error(
        self, post_model: Post, test_client_ex: TestClient
    ):
        response = test_client_ex.put(
            f'/api/v1/posts/{post_model.id}',
            json={'author': 'aa'},
        )
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 4

    async def test_fail_to_update_post_due_to_empty_authorization_header(
        self, json_body: str, post_model: Post, test_client: TestClient
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': ''},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_expired_bearer_token(
        self,
        json_body: str,
        jwt_token: JWTToken,
        post_model: Post,
        settings: Settings,
        test_client: TestClient,
    ):
        expired_jwt_token = copy.deepcopy(jwt_token)
        past = pendulum.now().subtract(months=1)
        expired_jwt_token.exp = past.add(hours=1).int_timestamp
        expired_jwt_token.iat = past.int_timestamp
        expired_jwt_token.sub['created_at'] = past.to_iso8601_string()
        token = jwt.encode(expired_jwt_token.dict(), key=settings.jwt_secret)
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': f'Bearer {token}'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_invalid_authorization_header(
        self, json_body: str, post_model: Post, test_client: TestClient
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': 'asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_blacklisted_bearer_token(
        self,
        mocker,
        cache_service: CacheService,
        json_body: str,
        jwt_token: JWTToken,
        post_model: Post,
        settings: Settings,
        test_client: TestClient,
    ):
        mocker.patch(
            'app.services.cache.CacheService.get',
            return_value=True,
        )
        token = jwt.encode(jwt_token.dict(), key=settings.jwt_secret)
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': f'Bearer {token}'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3
        cache_service.get.assert_called_once_with(f'jti_{jwt_token.jti}')

    async def test_fail_to_update_post_due_to_client_error(
        self,
        mocker,
        json_body: str,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        mocker.patch(
            self.POST_SERVICE_UPDATE_POST,
            side_effect=ClientError(error_response={}, operation_name='query'),
        )
        response = test_client_ex.put(f'/api/v1/posts/{post_model.id}', json=json_body)
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert len(response.json()) == 3
        post_service.update_post.assert_called_once_with(post_model.id, ANY)

    async def test_fail_to_update_post_due_to_invalid_bearer_token(
        self, json_body: str, post_model: Post, test_client: TestClient
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': 'Bearer asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_post_not_found_exception(
        self,
        mocker,
        json_body: str,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            self.POST_SERVICE_UPDATE_POST,
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = test_client_ex.put(f'/api/v1/posts/{post_model.id}', json=json_body)
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert error_message == response.json()['message']
        assert len(response.json()) == 3
        post_service.update_post.assert_called_once_with(post_model.id, ANY)

    async def test_fail_to_update_post_due_to_unauthorized(
        self, json_body: str, post_model: Post, test_client_ex_without_roles: TestClient
    ):
        response = test_client_ex_without_roles.put(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert len(response.json()) == 3

    async def test_successfully_update_post(
        self,
        mocker,
        json_body: str,
        post_model: Post,
        post_service: PostService,
        test_client_ex: TestClient,
    ):
        mocker.patch(self.POST_SERVICE_UPDATE_POST, return_value=post_model)
        response = test_client_ex.put(f'/api/v1/posts/{post_model.id}', json=json_body)
        assert status.HTTP_204_NO_CONTENT == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        post_service.update_post.assert_called_once_with(post_model.id, ANY)

    async def test_successfully_get_archive(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        mocker.patch(
            'app.services.post.PostService.get_archive',
            return_value={pendulum.parse(post_model.published_at).format('YYYY-MM'): 1},
        )
        response = test_client.get(f'/api/v1/posts/archive')
        assert status.HTTP_200_OK == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        json = response.json()
        assert 1 == len(json)
        assert 1 == json.get(pendulum.parse(post_model.published_at).format('YYYY-MM'))
        post_service.get_archive.assert_called_once()

    async def test_successfully_get_post_by_date_and_slug(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        dt = pendulum.parse(post_model.published_at)
        mocker.patch(
            'app.services.post.PostService.get_post_by_date_and_slug',
            return_value=PostResponse(**post_model.dict()),
        )
        response = test_client.get(
            f'/api/v1/posts/{dt.year}/{dt.month}/{dt.day}/{post_model.slug}'
        )
        assert status.HTTP_200_OK == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        json = response.json()
        assert post_model.id == json.get('id')
        assert dt == pendulum.parse(json.get('publishedAt'))

    async def test_fail_to_get_post_by_date_and_slug_due_to_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        test_client: TestClient,
    ):
        dt = pendulum.parse(post_model.published_at)
        mocker.patch(
            'app.services.post.PostService.get_post_by_date_and_slug',
            side_effect=PostNotFoundException('Post not found'),
        )
        response = test_client.get(
            f'/api/v1/posts/{dt.year}/{dt.month}/{dt.day}/{post_model.slug}'
        )
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert correlation_id.get() == response.headers.get(self.X_CORRELATION_ID)
        assert 'Post not found' == response.json().get('message')
