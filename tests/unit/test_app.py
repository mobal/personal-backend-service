import copy
import uuid

import jwt
import pendulum
import pytest
from fastapi import HTTPException
from starlette import status
from starlette.testclient import TestClient

from app.models.cache import Cache
from app.models.post import Post
from app.schemas.post import CreatePost
from app.services.post import PostService

BODY = {
    'author': 'root',
    'title': 'Some random title',
    'content': 'Some random content',
}
INVALID_AUTHENTICATION_TOKEN = 'Invalid authentication token'
NOT_AUTHENTICATED = 'Not authenticated'


@pytest.mark.asyncio
class TestApp:
    @pytest.fixture
    def authenticated_test_client(self, jwt_token, test_client) -> TestClient:
        from app.api.v1.routes.posts import jwt_bearer

        test_client.app.dependency_overrides[jwt_bearer] = lambda: jwt_token
        return test_client

    @pytest.fixture(autouse=True)
    def clear_dependency_overrides(self, test_client):
        test_client.app.dependency_overrides = {}

    @pytest.fixture
    def post_model(self) -> Post:
        now = pendulum.now()
        return Post(
            id=str(uuid.uuid4()),
            author=BODY['author'],
            title=BODY['title'],
            content=BODY['content'],
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

    async def test_fail_to_create_post_due_to_authorization_error(self, test_client):
        response = test_client.post(f'/api/v1/posts', json=None)
        assert status.HTTP_403_FORBIDDEN == response.status_code

    async def test_fail_to_create_post_due_to_invalid_body(
        self, authenticated_test_client
    ):
        response = authenticated_test_client.post(f'/api/v1/posts', json=None)
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert len(response.json()) == 4

    async def test_successfully_create_post(
        self, mocker, authenticated_test_client, post_model, post_service
    ):
        mocker.patch(
            'app.services.post.PostService.create_post', return_value=post_model
        )
        response = authenticated_test_client.post(f'/api/v1/posts', json=BODY)
        assert status.HTTP_201_CREATED == response.status_code
        assert 'location' in response.headers
        post_service.create_post.assert_called_once_with(CreatePost.parse_obj(BODY))

    @pytest.mark.asyncio
    async def test_successfully_get_post(
        self, mocker, test_client, post_model, post_service
    ):
        mocker.patch('app.services.post.PostService.get_post', return_value=post_model)
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_200_OK == response.status_code
        assert post_model == Post.parse_obj(response.json())
        post_service.get_post.assert_called_once_with(post_model.id)

    @pytest.mark.asyncio
    async def test_fail_to_get_post(
        self, mocker, test_client, post_model, post_service
    ):
        mocker.patch(
            'app.services.post.PostService.get_post',
            side_effect=HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'The requested post was not found with id {post_model.id}',
            ),
        )
        response = test_client.get(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_404_NOT_FOUND == response.status_code
        json = response.json()
        assert len(json) == 3
        assert post_model.id in json['message']
        post_service.get_post.assert_called_once_with(post_model.id)

    @pytest.mark.asyncio
    async def test_successfully_get_all_posts(
        self, mocker, test_client, post_model, post_service
    ):
        mocker.patch(
            'app.services.post.PostService.get_all_posts', return_value=[post_model]
        )
        response = test_client.get(f'/api/v1/posts')
        assert status.HTTP_200_OK == response.status_code
        json = response.json()
        assert len(json) == 1
        assert post_model.id == json[0]['id']
        post_service.get_all_posts.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_to_delete_post_due_to_authorization_error(
        self, test_client, post_model
    ):
        response = test_client.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_403_FORBIDDEN == response.status_code

    @pytest.mark.asyncio
    async def test_successfully_delete_post(
        self, mocker, authenticated_test_client, post_model, post_service
    ):
        mocker.patch('app.services.post.PostService.delete_post', return_value=None)
        response = authenticated_test_client.delete(f'/api/v1/posts/{post_model.id}')
        assert status.HTTP_204_NO_CONTENT == response.status_code
        post_service.delete_post.assert_called_once_with(post_model.id)

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_missing_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.put(f'/api/v1/posts/{post_model.id}')
        assert NOT_AUTHENTICATED == response.json()['message']
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_validation_error(
        self, authenticated_test_client, post_model
    ):
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}', json={}
        )
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert len(response.json()) == 4

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_empty_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}', json=BODY, headers={'Authorization': ''}
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_expired_bearer_token(
        self, test_client, settings, jwt_token, post_model
    ):
        expired_jwt_token = copy.deepcopy(jwt_token)
        past = pendulum.now().subtract(months=1)
        expired_jwt_token.exp = past.add(hours=1).int_timestamp
        expired_jwt_token.iat = past.int_timestamp
        expired_jwt_token.sub['created_at'] = past.to_iso8601_string()
        token = jwt.encode(expired_jwt_token.dict(), key=settings.jwt_secret)
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=BODY,
            headers={'Authorization': f'Bearer {token}'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_invalid_authorization_header(
        self, test_client, post_model
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=BODY,
            headers={'Authorization': 'asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert NOT_AUTHENTICATED == response.json()['message']
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_blacklisted_bearer_token(
        self, mocker, test_client, settings, jwt_token, post_model
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
            json=BODY,
            headers={'Authorization': f'Bearer {token}'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_fail_to_update_post_due_to_invalid_bearer_token(
        self, test_client, post_model
    ):
        response = test_client.put(
            f'/api/v1/posts/{post_model.id}',
            json=BODY,
            headers={'Authorization': 'Bearer asdf'},
        )
        assert status.HTTP_403_FORBIDDEN == response.status_code
        assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_successfully_update_post(
        self, mocker, authenticated_test_client, post_model
    ):
        mocker.patch(
            'app.services.post.PostService.update_post', return_value=post_model
        )
        response = authenticated_test_client.put(
            f'/api/v1/posts/{post_model.id}', json=BODY
        )
        assert status.HTTP_204_NO_CONTENT == response.status_code
