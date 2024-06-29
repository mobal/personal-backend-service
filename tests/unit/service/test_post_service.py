from unittest.mock import ANY

import pendulum
import pytest
from pytest_mock import MockerFixture
from starlette import status

from app.exceptions import PostAlreadyExistsException, PostNotFoundException
from app.models.post import Post
from app.models.response import Post as PostResponse
from app.repositories.post_repository import PostRepository
from app.schemas.post_schema import CreatePost, UpdatePost
from app.services.post_service import PostService

ERROR_MESSAGE_POST_WAS_NOT_FOUND = "The requested post was not found"
ERROR_MESSAGE_POST_ALREADY_EXISTS = "There is already a post with this title"


@pytest.mark.asyncio
class TestPostService:
    @pytest.fixture
    def post_service(self) -> PostService:
        return PostService()

    async def test_successfully_create_post(
        self,
        mocker: MockerFixture,
        make_post,
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(PostRepository, "get_post_by_title", return_value=None)
        mocker.patch.object(PostRepository, "create_post")

        post = make_post()
        result = await post_service.create_post(CreatePost(**post.model_dump()))

        assert post.author == result.author
        assert post.content == result.content
        assert post.meta == result.meta
        assert post.published_at == result.published_at
        assert post.tags == result.tags
        assert post.title == result.title
        assert result.is_deleted is False
        post_repository.get_post_by_title.assert_called_once_with(post.title, ANY)
        post_repository.create_post.assert_called_once()

    async def test_fail_to_create_post_due_to_already_exists_by_title(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(
            PostRepository, "get_post_by_title", return_value=posts[0].model_dump()
        )

        with pytest.raises(PostAlreadyExistsException) as excinfo:
            await post_service.create_post(CreatePost(**posts[0].model_dump()))

        assert status.HTTP_409_CONFLICT == excinfo.value.status_code
        assert ERROR_MESSAGE_POST_ALREADY_EXISTS == excinfo.value.detail
        post_repository.get_post_by_title.assert_called_once_with(posts[0].title, ANY)

    async def test_successfully_delete_post(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(
            PostRepository, "get_post_by_uuid", return_value=posts[0].model_dump()
        )
        mocker.patch.object(PostRepository, "update_post")

        await post_service.delete_post(posts[0].id)

        post_repository.get_post_by_uuid.assert_called_once_with(posts[0].id, ANY)
        post_repository.update_post.assert_called_once_with(posts[0].id, ANY, ANY)

    async def test_fail_to_delete_post_by_uuid_due_post_not_found_exception(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(PostRepository, "get_post_by_uuid", return_value=None)

        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.delete_post(posts[0].id)

        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert ERROR_MESSAGE_POST_WAS_NOT_FOUND == excinfo.value.detail
        post_repository.get_post_by_uuid.assert_called_once_with(posts[0].id, ANY)

    async def test_successfully_get_all_posts(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(
            PostRepository, "get_all_posts", return_value=[posts[0].model_dump()]
        )

        result = await post_service.get_all_posts()

        assert result.exclusive_start_key is None
        assert len(result.data) == 1
        assert PostResponse(**posts[0].model_dump()) == result.data[0]
        post_repository.get_all_posts.assert_called_once()

    async def test_successfully_get_post_by_uuid(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(
            PostRepository, "get_post_by_uuid", return_value=posts[0].model_dump()
        )

        result = await post_service.get_post(posts[0].id)

        assert PostResponse(**result.model_dump()) == result
        post_repository.get_post_by_uuid.assert_called_once_with(posts[0].id, ANY)

    async def test_fail_to_get_post_by_uuid_due_post_not_found_exception(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(PostRepository, "get_post_by_uuid", return_value=None)

        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.get_post(posts[0].id)

        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert ERROR_MESSAGE_POST_WAS_NOT_FOUND == excinfo.value.detail
        post_repository.get_post_by_uuid.assert_called_once_with(posts[0].id, ANY)

    async def test_successfully_update_post(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ) -> None:
        mocker.patch.object(
            PostRepository, "get_post_by_uuid", return_value=posts[0].model_dump()
        )
        mocker.patch.object(PostRepository, "update_post")

        update_post = UpdatePost(content="Updated content", title="Updated title")

        await post_service.update_post(posts[0].id, update_post)
        post_repository.update_post.assert_called_once_with(posts[0].id, ANY, ANY)

    async def test_fail_to_update_post_due_post_not_found_exception(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_repository: PostRepository,
        post_service: PostService,
    ):
        mocker.patch.object(PostRepository, "get_post_by_uuid", return_value=None)

        update_post = UpdatePost(**{"content": "Updated content"})

        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.update_post(posts[0].id, update_post)

        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert ERROR_MESSAGE_POST_WAS_NOT_FOUND == excinfo.value.detail
        post_repository.get_post_by_uuid.assert_called_once_with(posts[0].id, ANY)

    async def test_successfully_get_archive(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_service: PostService,
    ):
        mocker.patch.object(
            PostRepository, "get_all_posts", return_value=[posts[0].model_dump()]
        )

        result = await post_service.get_archive()

        assert result.get(pendulum.parse(posts[0].published_at).format("YYYY-MM")) == 1

    async def test_successfully_get_archive_and_return_none(
        self,
        mocker: MockerFixture,
        post_service: PostService,
    ):
        mocker.patch.object(PostRepository, "get_all_posts", return_value=[])

        result = await post_service.get_archive()

        assert 0 == len(result)

    async def test_successfully_get_post_by_post_path(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch.object(
            PostRepository, "get_post_by_post_path", return_value=posts[0].model_dump()
        )

        dt = pendulum.parse(posts[0].published_at)
        post_path = f"{dt.year}/{dt.month}/{dt.day}/{posts[0].slug}"
        result = await post_service.get_by_post_path(post_path)

        assert posts[0].slug == result.slug
        assert posts[0].published_at == result.published_at
        post_repository.get_post_by_post_path.assert_called_once_with(post_path, ANY)

    async def test_fail_to_get_post_by_post_path_due_post_not_found_exception(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        post_service: PostService,
        post_repository: PostRepository,
    ):
        mocker.patch.object(PostRepository, "get_post_by_post_path", return_value=None)

        dt = pendulum.parse(posts[0].published_at)
        post_path = f"{dt.year}/{dt.month}/{dt.day}/{posts[0].slug}"
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_service.get_by_post_path(post_path)

        assert PostNotFoundException.__name__ == excinfo.typename
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert ERROR_MESSAGE_POST_WAS_NOT_FOUND == excinfo.value.detail
        post_repository.get_post_by_post_path.assert_called_once_with(post_path, ANY)
