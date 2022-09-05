from unittest.mock import ANY

import pendulum
import pytest
from starlette import status

from app.exceptions import PostNotFoundException
from app.models.post import Post
from app.models.response import Post as PostResponse
from app.repositories.post import PostRepository
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService


@pytest.mark.asyncio
class TestPostService:
    PROFILE_REPOSITORY_GET_ALL_POSTS = (
        'app.repositories.post.PostRepository.get_all_posts'
    )
    PROFILE_REPOSITORY_GET_POST_BY_UUID = (
        'app.repositories.post.PostRepository.get_post_by_uuid'
    )
    PROFILE_REPOSITORY_UPDATE_POST = 'app.repositories.post.PostRepository.update_post'

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
        mocker.patch('app.repositories.post.PostRepository.create_post')
        create_post = CreatePost(**post_dict)
        result = await post_service.create_post(create_post)
        assert post_dict['author'] == result.author
        assert post_dict['content'] == result.content
        assert post_dict['meta'] == result.meta
        assert post_dict['published_at'] == result.published_at
        assert post_dict['tags'] == result.tags
        assert post_dict['title'] == result.title
        assert result.is_deleted is False
        post_repository.create_post.assert_called_once()

    async def test_successfully_delete_post(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_POST_BY_UUID, return_value=post_model.dict()
        )
        mocker.patch(self.PROFILE_REPOSITORY_UPDATE_POST)
        await post_service.delete_post(post_model.id)
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)
        post_repository.update_post.assert_called_once_with(post_model.id, ANY, ANY)

    async def test_fail_to_delete_post_by_uuid_due_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_POST_BY_UUID,
            side_effect=PostNotFoundException(
                f'Post was not found with UUID post_uuid={post_model.id}'
            ),
        )
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.delete_post(post_model.id)
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert (
            f'Post was not found with UUID post_uuid={post_model.id}'
            == excinfo.value.detail
        )
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)

    async def test_successfully_get_all_posts(
        self,
        mocker,
        post_fields: str,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_ALL_POSTS,
            return_value=[post_model.dict()],
        )
        result = await post_service.get_all_posts(post_fields)
        assert len(result) == 1
        assert PostResponse(**post_model.dict()) == result[0]
        post_repository.get_all_posts.assert_called_once()

    async def test_successfully_get_post_by_uuid(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_POST_BY_UUID,
            return_value=post_model.dict(),
        )
        result = await post_service.get_post(post_model.id)
        assert PostResponse(**result.dict()) == result
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)

    async def test_fail_to_get_post_by_uuid_due_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_POST_BY_UUID,
            side_effect=PostNotFoundException(
                f'Post was not found with UUID post_uuid={post_model.id}'
            ),
        )
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.get_post(post_model.id)
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert (
            f'Post was not found with UUID post_uuid={post_model.id}'
            == excinfo.value.detail
        )
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)

    async def test_successfully_update_post(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ) -> None:
        mocker.patch(self.PROFILE_REPOSITORY_UPDATE_POST)
        update_post = UpdatePost(content='Updated content', title='Updated title')
        await post_service.update_post(post_model.id, update_post)
        post_repository.update_post.assert_called_once_with(post_model.id, ANY, ANY)

    async def test_fail_to_update_post_due_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_POST_BY_UUID,
            side_effect=PostNotFoundException(
                f'Post was not found with UUID post_uuid={post_model.id}'
            ),
        )
        update_post = UpdatePost(**{'content': 'Updated content'})
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.update_post(post_model.id, update_post)
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert (
            f'Post was not found with UUID post_uuid={post_model.id}'
            == excinfo.value.detail
        )
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)

    async def test_successfully_get_archive(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_ALL_POSTS,
            return_value=[post_model.dict()],
        )
        result = await post_service.get_archive()
        assert (
            result.get(pendulum.parse(post_model.published_at).format('YYYY-MM')) == 1
        )

    async def test_successfully_get_archive_and_return_none(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch(
            self.PROFILE_REPOSITORY_GET_ALL_POSTS,
            return_value=[],
        )
        result = await post_service.get_archive()
        assert 0 == len(result)

    async def test_successfully_get_post_by_date_and_slug(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch(
            'app.repositories.post.PostRepository.get_post',
            return_value=post_model.dict(),
        )
        dt = pendulum.parse(post_model.published_at)
        result = await post_service.get_post_by_date_and_slug(
            dt.year, dt.month, dt.day, post_model.slug
        )
        assert post_model.slug == result.slug
        assert post_model.published_at == result.published_at
        post_repository.get_post.assert_called_once()

    async def test_fail_to_get_post_by_date_and_slug_due_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch(
            'app.repositories.post.PostRepository.get_post',
            side_effect=PostNotFoundException('Post was not found'),
        )
        dt = pendulum.parse(post_model.published_at)
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.get_post_by_date_and_slug(
                dt.year, dt.month, dt.day, post_model.slug
            )
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert f'Post was not found' == excinfo.value.detail
        post_repository.get_post.assert_called_once()
