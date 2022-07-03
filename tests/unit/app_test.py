import copy

import jwt
import pendulum
import pytest
from starlette import status
from starlette.testclient import TestClient

from app.api.v1.routes.posts import jwt_auth
from app.auth import JWTToken
from app.main import app
from app.models.cache import Cache
from app.models.post import Post
from app.schemas.post import CreatePost
from app.services.post import PostService

INVALID_AUTHENTICATION_TOKEN = 'Invalid authentication token'
NOT_AUTHENTICATED = 'Not authenticated'


@pytest.fixture
def authenticated_test_client(jwt_token, test_client) -> TestClient:
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    return test_client


@pytest.fixture(autouse=True)
def before(test_client):
    test_client.app.dependency_overrides = {}


@pytest.fixture
def body() -> dict:
    return {'author': 'root', 'title': 'Lorem ipsum', 'content': 'Lorem ipsum'}


@pytest.fixture
def jwt_token() -> JWTToken:
    now = pendulum.now()
    return JWTToken(exp=now.add(hours=1).int_timestamp, iat=now.int_timestamp, iss='https://netcode.hu',
                    jti='7a93ffe1-34b8-42d1-b3da-90d5273da171', sub={'id': 'b5d21631-1c27-4e00-99ad-9de532daaca2',
                                                                     'email': 'info@netcode.hu', 'display_name': 'root',
                                                                     'roles': ['root'],
                                                                     'created_at': now.to_iso8601_string(),
                                                                     'deleted_at': None, 'updated_at': None})


@pytest.fixture
def post_model(body) -> Post:
    now = pendulum.now()
    return Post(id='2fa3f28e-553d-4398-93c8-fd434436657b', author=body['author'], title=body['title'],
                content=body['content'], created_at=now.to_iso8601_string(), deleted_at=None,
                published_at=now.to_iso8601_string(), updated_at=None, slug='lorem-ipsum', tags=['lorem', 'ipsum'])


@pytest.fixture
def post_service() -> PostService:
    return PostService()


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_authorization_error(test_client):
    response = test_client.post(f'/api/v1/posts', json=None)
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_authorization_error(test_client, body):
    response = test_client.post(f'/api/v1/posts', json=body)
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_invalid_body(authenticated_test_client, jwt_token, post_model):
    response = authenticated_test_client.post(f'/api/v1/posts', json=None)
    assert status.HTTP_400_BAD_REQUEST == response.status_code
    assert len(response.json()) == 4


@pytest.mark.asyncio
async def test_successfully_create_post(mocker, authenticated_test_client, body, jwt_token, post_model, post_service):
    mocker.patch('app.services.post.PostService.create_post',
                 return_value=post_model)
    response = authenticated_test_client.post(f'/api/v1/posts', json=body)
    assert status.HTTP_201_CREATED == response.status_code
    assert 'location' in response.headers
    post_service.create_post.assert_called_once_with(
        CreatePost.parse_obj(body))


@pytest.mark.asyncio
async def test_successfully_get_post(mocker, test_client, post_model, post_service):
    mocker.patch('app.services.post.PostService.get_post',
                 return_value=post_model)
    response = test_client.get(f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_200_OK == response.status_code
    assert post_model == Post.parse_obj(response.json())
    post_service.get_post.assert_called_once_with(post_model.id)


@pytest.mark.asyncio
async def test_fail_to_get_post(mocker, test_client, post_model, post_service):
    mocker.patch('app.services.post.PostService.get_post', return_value=None)
    response = test_client.get(f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_404_NOT_FOUND == response.status_code
    json = response.json()
    assert len(json) == 3
    assert post_model.id in json['message']
    post_service.get_post.assert_called_once_with(post_model.id)


@pytest.mark.asyncio
async def test_successfully_get_all_posts(mocker, test_client, post_model, post_service):
    mocker.patch('app.services.post.PostService.get_all_posts',
                 return_value=[post_model])
    response = test_client.get(f'/api/v1/posts')
    assert status.HTTP_200_OK == response.status_code
    json = response.json()
    assert len(json) == 1
    assert post_model.id == json[0]['id']
    post_service.get_all_posts.assert_called_once()


@pytest.mark.asyncio
async def test_fail_to_delete_post_due_to_authorization_error(test_client, post_model):
    response = test_client.delete(f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_successfully_delete_post(mocker, authenticated_test_client, jwt_token, post_model, post_service):
    mocker.patch('app.services.post.PostService.delete_post',
                 return_value=None)
    response = authenticated_test_client.delete(
        f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_204_NO_CONTENT == response.status_code
    post_service.delete_post.assert_called_once_with(post_model.id)


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_missing_authorization_header(test_client, post_model):
    response = test_client.put(f'/api/v1/posts/{post_model.id}')
    assert NOT_AUTHENTICATED == response.json()['message']
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_validation_error(authenticated_test_client, jwt_token, post_model):
    response = authenticated_test_client.put(
        f'/api/v1/posts/{post_model.id}', json={})
    assert status.HTTP_400_BAD_REQUEST == response.status_code
    assert len(response.json()) == 4


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_empty_authorization_header(test_client, body, post_model):
    response = test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body, headers={'Authorization': ''})
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert NOT_AUTHENTICATED == response.json()['message']
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_expired_bearer_token(test_client, body, config, jwt_token, post_model):
    expired_jwt_token = copy.deepcopy(jwt_token)
    past = pendulum.now().subtract(months=1)
    expired_jwt_token.exp = past.add(hours=1).int_timestamp
    expired_jwt_token.iat = past.int_timestamp
    expired_jwt_token.sub['created_at'] = past.to_iso8601_string()
    token = jwt.encode(expired_jwt_token.dict(), key=config.jwt_secret)
    response = test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body, headers={'Authorization': f'Bearer {token}'})
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_invalid_authorization_header(test_client, body, post_model):
    response = test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body, headers={'Authorization': 'asdf'})
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert NOT_AUTHENTICATED == response.json()['message']
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_blacklisted_bearer_token(mocker, test_client, body, config, jwt_token,
                                                                   post_model):
    now = pendulum.now()
    mocker.patch('app.services.cache.CacheService.get',
                 return_value=Cache(key='jti', value=jwt_token.jti, expired_at=now.add(years=1).to_iso8601_string()))
    token = jwt.encode(jwt_token.dict(), key=config.jwt_secret)
    response = test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body, headers={'Authorization': f'Bearer {token}'})
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_invalid_bearer_token(test_client, body, post_model):
    response = test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body, headers={'Authorization': 'Bearer asdf'})
    assert status.HTTP_403_FORBIDDEN == response.status_code
    assert INVALID_AUTHENTICATION_TOKEN == response.json()['message']
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_successfully_update_post(mocker, authenticated_test_client, body, jwt_token, post_model, post_service):
    mocker.patch('app.services.post.PostService.update_post',
                 return_value=post_model)
    response = authenticated_test_client.put(
        f'/api/v1/posts/{post_model.id}', json=body)
    assert status.HTTP_204_NO_CONTENT == response.status_code
