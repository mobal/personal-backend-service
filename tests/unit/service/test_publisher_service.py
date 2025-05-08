from unittest.mock import MagicMock

import pendulum
import pytest
from pytest_mock import MockerFixture

from app.models.post import Post
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService


class TestPublisherService:
    @pytest.fixture
    def mock_fs(self):
        return MagicMock()

    @pytest.fixture
    def mock_sshfs(self, mocker: MockerFixture):
        return mocker.patch("app.services.publisher_service.SSHFileSystem")

    def test_successfully_publish(
        self,
        mocker: MockerFixture,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_stream

        publisher_service.publish(posts[0].id)

        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        mock_sshfs.assert_called_once()
        mock_fs.open.assert_called_once_with(posts[0].post_path, "wb")
        mock_stream.write.assert_called_once_with(posts[0].content.encode("utf-8"))

    def test_publish_future_post(
        self,
        mock_sshfs: MagicMock,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
    ):
        posts[0].published_at = pendulum.now().add(days=1).to_iso8601_string()
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])

        publisher_service.publish(posts[0].id)

        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        mock_sshfs.assert_not_called()

    def test_successfully_remove_path(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        posts: list[Post],
        publisher_service: PublisherService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_stream

        publisher_service.rm(posts[0].post_path)

        mock_sshfs.assert_called_once()
        mock_fs.rm.assert_called_once_with(posts[0].post_path)
