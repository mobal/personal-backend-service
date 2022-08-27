from unittest.mock import ANY

import pytest
from starlette import status

from app.exception import PostNotFoundException
from app.models.post import Post
from app.models.response import Post as PostResponse
from app.repositories.post import PostRepository
from app.services.post import PostService


@pytest.mark.asyncio
class TestPostService:
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
            'app.repositories.post.PostRepository.create_post', return_value=post_model
        )
        result = await post_service.create_post(post_dict)
        for k, v in post_dict.items():
            assert v == getattr(result, k)
        assert result.is_deleted is False
        post_repository.create_post.assert_called_once_with(post_dict)

    async def test_successfully_delete_post(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch('app.repositories.post.PostRepository.get_post_by_uuid')
        mocker.patch('app.repositories.post.PostRepository.update_post')
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
            'app.repositories.post.PostRepository.get_post_by_uuid',
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
        post_fields,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repositories.post.PostRepository.get_all_posts',
            return_value=[post_model.dict()],
        )
        result = await post_service.get_all_posts(post_fields)
        assert len(result) == 1
        assert PostResponse(**post_model.dict()) == result[0]
        post_repository.get_all_posts.assert_called_once_with(ANY, ANY)

    async def test_successfully_get_post_by_uuid(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repositories.post.PostRepository.get_post_by_uuid',
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
            'app.repositories.post.PostRepository.get_post_by_uuid',
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
        mocker.patch('app.repositories.post.PostRepository.update_post')
        data = {'content': 'Updated content'}
        await post_service.update_post(post_model.id, data)
        post_repository.update_post.assert_called_once_with(post_model.id, data, ANY)

    async def test_fail_to_update_post_due_post_not_found_exception(
        self,
        mocker,
        post_model: Post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch(
            'app.repositories.post.PostRepository.get_post_by_uuid',
            side_effect=PostNotFoundException(
                f'Post was not found with UUID post_uuid={post_model.id}'
            ),
        )
        data = {'content': 'Updated content'}
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.update_post(post_model.id, data)
        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert (
            f'Post was not found with UUID post_uuid={post_model.id}'
            == excinfo.value.detail
        )
        post_repository.get_post_by_uuid.assert_called_once_with(post_model.id, ANY)
