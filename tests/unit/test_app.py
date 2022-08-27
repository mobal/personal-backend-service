import copy
import uuid
from unittest.mock import ANY

import jwt
import pendulum
import pytest
from botocore.exceptions import ClientError
from starlette import status
from starlette.testclient import TestClient

from app.exception import PostNotFoundException
from app.models.cache import Cache
from app.models.post import Post
from app.schemas.post import CreatePost
from app.services.post import PostService


@pytest.mark.asyncio
class TestApp:
    NOT_AUTHENTICATED = 'Not authenticated'
    NOT_AUTHORIZED = 'Not authorized'
    POST_SERVICE_UPDATE_POST = 'app.services.post.PostService.update_post'

    @pytest.fixture
    def authenticated_test_client(self, jwt_token, test_client) -> TestClient:
        from app.api.v1.routes.posts import jwt_bearer

        test_client.app.dependency_overrides[jwt_bearer] = lambda: jwt_token
        return test_client

    @pytest.fixture
    def authenticated_test_client_without_roles(
        self, jwt_token_without_roles, test_client
    ) -> TestClient:
        from app.api.v1.routes.posts import jwt_bearer

        test_client.app.dependency_overrides[
            jwt_bearer
        ] = lambda: jwt_token_without_roles
        return test_client

    @pytest.fixture(autouse=True)
    def clear_dependency_overrides(self, test_client):
        test_client.app.dependency_overrides = {}

    @pytest.fixture
    def json_body(self) -> dict:
        return {
            'author': 'root',
            'title': 'Some random title',
            'content': 'Some random content',
        }

    @pytest.fixture
    def post_model(self, json_body) -> Post:
        now = pendulum.now()
        return Post(
            id=str(uuid.uuid4()),
            author=json_body.get('author'),
            title=json_body.get('title'),
            content=json_body.get('content'),
            created_at=now.to_iso8601_string(),
            deleted_at=None,
            published_at=now.to_iso8601_string(),
            updated_at=None,
            slug='lorem-ipsum',
            tags=['lorem', 'ipsum'],
        )

    @pytest.fixture
    def post_service(self) -> PostService:
        return PostService()

    @pytest.fixture
    def test_client(self) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_fail_to_create_post_due_to_invalid_body(
        self, authenticated_test_client
    ):
        response = authenticated_test_client.post(f'/api/v1/posts', json=None)
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert len(response.json()) == 4

    async def test_fail_to_create_post_due_to_empty_authorization_header(
        self, json_body, test_client
    ):
        response = test_client.post(
            f'/api/v1/posts', headers={'Authorization': None}, json=json_body
        )
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_create_post_due_to_missing_authorization_header(
        self, json_body, test_client
    ):
        response = test_client.post(f'/api/v1/posts', json=json_body)
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_create_post_due_to_unauthorized(
        self, authenticated_test_client_without_roles, json_body
    ):
        response = authenticated_test_client_without_roles.post(
            f'/api/v1/posts', json=json_body
        )
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert len(response.json()) == 3

    async def test_successfully_create_post(
        self, mocker, authenticated_test_client, json_body, post_model, post_service
    ):
        mocker.patch(
            'app.services.post.PostService.create_post', return_value=post_model
        )
        response = authenticated_test_client.post(f'/api/v1/posts', json=json_body)
        assert status.HTTP_201_CREATED == response.status_code
        assert 'location' in response.headers
        post_service.create_post.assert_called_once_with(
            CreatePost.parse_obj(json_body)
        )

    async def test_successfully_get_post(
        self, mocker, post_model, post_service, test_client
    ):
        mocker.patch('app.services.post.PostService.get_post', return_value=post_model)
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_200_OK == response.status_code
        assert post_model == Post.parse_obj(response.json())
        post_service.get_post.assert_called_once_with(post_model.id)

    async def test_fail_to_get_post_due_to_post_not_found_exception(
        self, mocker, post_model, post_service, test_client
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            'app.services.post.PostService.get_post',
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert error_message == response.json()['message']
        json = response.json()
        assert len(json) == 3
        post_service.get_post.assert_called_once_with(post_model.id)

    async def test_successfully_get_all_posts(
        self, mocker, post_fields, post_model, post_service, test_client
    ):
        mocker.patch(
            'app.services.post.PostService.get_all_posts', return_value=[post_model]
        )
        response = test_client.get(f'/api/v1/posts?fields={post_fields}')
        assert status.HTTP_200_OK == response.status_code
        json = response.json()
        assert len(json) == 1
        assert post_model.id == json[0]['id']
        post_service.get_all_posts.assert_called_once()

    async def test_fail_to_delete_post_due_to_post_not_found_exception(
        self,
        mocker,
        authenticated_test_client,
        json_body,
        post_model,
        post_service,
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            'app.services.post.PostService.delete_post',
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = authenticated_test_client.delete(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert error_message == response.json()['message']
        assert len(response.json()) == 3
        post_service.delete_post.assert_called_once_with(post_model.id)

    async def test_successfully_delete_post(
        self, mocker, authenticated_test_client, post_model, post_service
    ):
        mocker.patch('app.services.post.PostService.delete_post', return_value=None)
        response = authenticated_test_client.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_204_NO_CONTENT == response.status_code
        post_service.delete_post.assert_called_once_with(post_model.id)

    async def test_fail_to_delete_post_due_to_empty_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.delete(
            f'/api/v1/posts/{post_model.id}', headers={'Authorization': None}
        )
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_delete_post_due_to_missing_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.delete(f'/api/v1/posts/{post_model.id}')
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_delete_post_due_to_unauthorized(
        self, authenticated_test_client_without_roles, post_model
    ):
        response = authenticated_test_client_without_roles.delete(
            f'/api/v1/posts/{post_model.id}'
        )
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_missing_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.put(f'/api/v1/posts/{post_model.id}')
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_validation_error(
        self, authenticated_test_client, post_model
    ):
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json={'deletedAt': pendulum.now().to_iso8601_string()},
        )
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert len(response.json()) == 4

    async def test_fail_to_update_post_due_to_empty_authorization_header(
        self, json_body, post_model, test_client
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': ''},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_expired_bearer_token(
        self, json_body, jwt_token, post_model, settings, test_client
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
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_invalid_authorization_header(
        self, json_body, post_model, test_client
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': 'asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_blacklisted_bearer_token(
        self, mocker, json_body, jwt_token, post_model, settings, test_client
    ):
        now = pendulum.now()
        mocker.patch(
            'app.services.cache.CacheService.get',
            return_value=Cache(
                key='jti',
                value=jwt_token.jti,
                created_at=now.add(years=1).to_iso8601_string(),
                ttl=now.add(years=1).int_timestamp,
            ),
        )
        token = jwt.encode(jwt_token.dict(), key=settings.jwt_secret)
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': f'Bearer {token}'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_client_error(
        self,
        mocker,
        authenticated_test_client,
        json_body,
        post_model,
        post_service,
    ):
        mocker.patch(
            self.POST_SERVICE_UPDATE_POST,
            side_effect=ClientError(error_response={}, operation_name='query'),
        )
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        assert len(response.json()) == 3
        post_service.update_post.assert_called_once_with(post_model.id, ANY)

    async def test_fail_to_update_post_due_to_invalid_bearer_token(
        self, json_body, test_client, post_model
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=json_body,
            headers={'Authorization': 'Bearer asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert self.NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    async def test_fail_to_update_post_due_to_post_not_found_exception(
        self,
        mocker,
        authenticated_test_client,
        json_body,
        post_model,
        post_service,
    ):
        error_message = f'Post was not found with UUID post_uuid={post_model.id}'
        mocker.patch(
            self.POST_SERVICE_UPDATE_POST,
            side_effect=PostNotFoundException(detail=error_message),
        )
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_404_NOT_FOUND == response.status_code
        assert error_message == response.json()['message']
        assert len(response.json()) == 3
        post_service.update_post.assert_called_once_with(post_model.id, ANY)

    async def test_fail_to_update_post_due_to_unauthorized(
        self, authenticated_test_client_without_roles, json_body, post_model
    ):
        response = authenticated_test_client_without_roles.put(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_401_UNAUTHORIZED == response.status_code
        assert self.NOT_AUTHORIZED == response.json()['message']
        assert len(response.json()) == 3

    async def test_successfully_update_post(
        self, mocker, authenticated_test_client, json_body, post_model
    ):
        mocker.patch(self.POST_SERVICE_UPDATE_POST, return_value=post_model)
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}', json=json_body
        )
        assert status.HTTP_204_NO_CONTENT == response.status_code
