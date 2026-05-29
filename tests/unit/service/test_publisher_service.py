import os
import uuid
from unittest.mock import MagicMock

import asyncssh
import pendulum
import pytest
from asyncssh import Error as SSHError
from fastapi import status
from pytest_mock import MockerFixture

from app.exceptions import PublishException
from app.models.post import Post
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService
from app.services.sshfs_storage_service import SSHFSStorageService

ERROR_MESSAGE: str = "error"


class TestPublisherService:
    def test_successfully_publish(
        self,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(SSHFSStorageService, "write")

        publisher_service.publish(posts[0].id)

        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()

    def test_publish_future_post(
        self,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].published_at = pendulum.now().add(days=1).to_iso8601_string()
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(SSHFSStorageService, "write")

        publisher_service.publish(posts[0].id)

        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_not_called()

    def test_fail_to_publish_due_to_ssh_error(
        self,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            SSHFSStorageService, "write", side_effect=SSHError(1, ERROR_MESSAGE)
        )

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()

    def test_fail_to_publish_due_to_os_error(
        self,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            SSHFSStorageService, "write", side_effect=OSError(ERROR_MESSAGE)
        )

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()

    def test_fail_to_publish_due_to_null_published_at(
        self,
        mocker: MockerFixture,
        mock_sshfs: MagicMock,
        post_service: PostService,
        publisher_service: PublisherService,
    ):
        post = Post(
            id=str(uuid.uuid4()),
            title="Test Post",
            content="Test content",
            post_path=str(uuid.uuid4()),
            author="Alice",
            created_at="2024-01-01",
            deleted_at=None,
            published_at=None,
            slug="test-post",
            tags=["test"],
            meta={
                "category": "test",
                "description": "Test desc",
                "language": "en",
                "keywords": ["k1"],
                "title": "Test",
            },
        )

        mocker.patch.object(PostService, "get_post_by_uuid", return_value=post)

        publisher_service.publish(post.id)

        post_service.get_post_by_uuid.assert_called_once_with(post.id)
        mock_sshfs.assert_not_called()
