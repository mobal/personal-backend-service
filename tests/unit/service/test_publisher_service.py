from unittest.mock import MagicMock

import asyncssh
import pendulum
import pytest
from pytest_mock import MockerFixture
from starlette import status

from app.exceptions import PublishException
from app.models.post import Post
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService

ERROR_MESSAGE: str = "error"


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

    def test_fail_to_publish_due_to_ssh_error(
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
        mock_stream.write.side_effect = asyncssh.Error(code=1, reason=ERROR_MESSAGE)

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        mock_sshfs.assert_called_once()
        mock_stream.write.assert_called_once_with(posts[0].content.encode("utf-8"))

    def test_fail_to_publish_due_to_os_error(
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
        mock_stream.write.side_effect = OSError(ERROR_MESSAGE)

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        mock_sshfs.assert_called_once()
        mock_stream.write.assert_called_once_with(posts[0].content.encode("utf-8"))

    def test_successfully_rm(
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

    def test_fail_to_rm_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        posts: list[Post],
        publisher_service: PublisherService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_stream
        mock_fs.rm.side_effect = asyncssh.Error(code=1, reason=ERROR_MESSAGE)

        with pytest.raises(PublishException) as excinfo:
            publisher_service.rm(posts[0].post_path)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        mock_sshfs.assert_called_once()
        mock_fs.rm.assert_called_once_with(posts[0].post_path)

    def test_fail_to_rm_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        posts: list[Post],
        publisher_service: PublisherService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_stream
        mock_fs.rm.side_effect = OSError(ERROR_MESSAGE)

        with pytest.raises(PublishException) as excinfo:
            publisher_service.rm(posts[0].post_path)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        mock_sshfs.assert_called_once()
        mock_fs.rm.assert_called_once_with(posts[0].post_path)
