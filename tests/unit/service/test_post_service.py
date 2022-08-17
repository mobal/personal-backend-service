import uuid

import pendulum
import pytest
from starlette import status

from app.exception import PostNotFoundException
from app.models.post import Post

from app.repository.post import PostRepository
from app.services.post import PostService


@pytest.mark.asyncio
class TestPostService:
    @pytest.fixture
    def post_dict(self) -> dict:
        tags = ['list', 'of', 'keywords']
        title = 'Some random title'
        return {
            'author': 'root',
            'title': title,
            'content': 'Some random content',
            'published_at': pendulum.now().to_iso8601_string(),
            'tags': tags,
            'meta': {
                'description': 'Meta description',
                'language': 'en',
                'keywords': tags,
                'title': title,
            },
        }

    @pytest.fixture
    def post_model(self, post_dict: dict) -> Post:
        post_uuid = str(uuid.uuid4())
        return Post.parse_obj(
            {
                'id': post_uuid,
                'author': post_dict['author'],
                'content': post_dict['content'],
                'created_at': pendulum.now().to_iso8601_string(),
                'deleted_at': None,
                'published_at': post_dict['published_at'],
                'slug': f'some-random-title-{post_uuid}',
                'tags': post_dict['tags'],
                'title': post_dict['title'],
                'updated_at': None,
                'meta': post_dict['meta'],
            }
        )

    @pytest.fixture
    def post_repository(self) -> PostRepository:
        return PostRepository()

    @pytest.fixture
    def post_service(self) -> PostService:
        return PostService()

    async def test_successfully_create_post(
        self,
        mocker,
        post_dict: dict,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repository.post.PostRepository.create_post', return_value=post_model
        )
        result = await post_service.create_post(post_dict)
        assert post_dict.get('author') == result.dict().get('author')
        assert post_dict.get('title') == result.dict().get('title')
        assert post_dict.get('content') == result.dict().get('content')
        assert post_dict.get('published_at') == result.dict().get('published_at')
        assert post_dict.get('tags') == result.dict().get('tags')
        assert post_dict.get('meta') == result.dict().get('meta')
        post_repository.create_post.assert_called_once_with(post_dict)

    async def test_successfully_delete_post(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch('app.repository.post.PostRepository.delete_post')
        await post_service.delete_post(post_model.id)
        post_repository.delete_post.assert_called_once_with(post_model.id)

    async def test_successfully_get_all_posts(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repository.post.PostRepository.get_all_posts',
            return_value=[post_model],
        )
        result = await post_service.get_all_posts()
        assert len(result) == 1
        assert post_model == result[0]
        post_repository.get_all_posts.assert_called_once()

    async def test_successfully_get_post_by_uuid(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repository.post.PostRepository.get_post_by_uuid',
            return_value=post_model,
        )
        result = await post_service.get_post(post_model.id)
        assert post_model == result
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id)

    async def test_fail_to_get_post_by_uuid(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repository.post.PostRepository.get_post_by_uuid',
            side_effect=PostNotFoundException(
                f'Post was not found with UUID post_uuid={post_model.id}'
            ),
        )
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.get_post(str(uuid.uuid4()))
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code

    async def test_successfully_update_post(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ) -> None:
        mocker.patch('app.repository.post.PostRepository.update_post')
        data = {'content', 'Updated content'}
        await post_service.update_post(post_model.id, data)
        post_repository.update_post.assert_called_once_with(post_model.id, data)
