import pytest
from starlette import status

from app.api.api_v1.endpoints.posts import jwt_auth
from app.models.post import Post
from app.schemas.post import CreatePost
from app.services.post import PostService


@pytest.fixture(autouse=True)
def before(test_client):
    test_client.app.dependency_overrides = {}


@pytest.fixture
def body() -> dict:
    return {'author': 'root', 'title': 'Lorem ipsum', 'content': 'Lorem ipsum'}


@pytest.fixture
def post_model() -> Post:
    return Post(id='2fa3f28e-553d-4398-93c8-fd434436657b', author='root', title='Lorem ipsum', content='Lorem ipsum',
                created_at='2022-06-23T20:49:17Z', deleted_at=None, published_at='2022-06-23T20:49:17Z',
                updated_at=None, slug='lorem-ipsum', tags=['lorem', 'ipsum'])


@pytest.fixture
def post_service() -> PostService:
    return PostService()


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_authorization_error(test_client):
    response = test_client.post(f'/api/v1/posts', json=None)
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_authorization_error(test_client, body):
    response = test_client.post(f'/api/v1/posts', json=body)
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_fail_to_create_post_due_to_invalid_body(test_client, jwt_token, post_model):
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    response = test_client.post(f'/api/v1/posts', json=None)
    assert status.HTTP_400_BAD_REQUEST == response.status_code
    assert len(response.json()) == 4


@pytest.mark.asyncio
async def test_successfully_create_post(mocker, test_client, body, jwt_token, post_model, post_service):
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    mocker.patch('app.services.post.PostService.create_post', return_value=post_model)
    response = test_client.post(f'/api/v1/posts', json=body)
    assert status.HTTP_201_CREATED == response.status_code
    assert 'location' in response.headers
    post_service.create_post.assert_called_once_with(CreatePost.parse_obj(body))


@pytest.mark.asyncio
async def test_successfully_get_post(mocker, test_client, post_model, post_service):
    mocker.patch('app.services.post.PostService.get_post', return_value=post_model)
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
    mocker.patch('app.services.post.PostService.get_all_posts', return_value=[post_model])
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
async def test_successfully_delete_post(mocker, test_client, jwt_token, post_model, post_service):
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    mocker.patch('app.services.post.PostService.delete_post', return_value=None)
    response = test_client.delete(f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_204_NO_CONTENT == response.status_code
    post_service.delete_post.assert_called_once_with(post_model.id)


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_authorization_error(test_client, post_model):
    response = test_client.put(f'/api/v1/posts/{post_model.id}')
    assert status.HTTP_403_FORBIDDEN == response.status_code


@pytest.mark.asyncio
async def test_fail_to_update_post_due_to_validation_error(test_client, jwt_token, post_model):
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    response = test_client.put(f'/api/v1/posts/{post_model.id}', json={})
    assert status.HTTP_400_BAD_REQUEST == response.status_code
    assert len(response.json()) == 4


@pytest.mark.asyncio
async def test_successfully_update_post(mocker, test_client, body, jwt_token, post_model, post_service):
    test_client.app.dependency_overrides[jwt_auth] = lambda: jwt_token
    mocker.patch('app.services.post.PostService.update_post', return_value=post_model)
    response = test_client.put(f'/api/v1/posts/{post_model.id}', json=body)
    assert status.HTTP_204_NO_CONTENT == response.status_code
