import uuid
from datetime import UTC, datetime, timedelta

import pytest
from asyncssh import Error as SSHError
from botocore.exceptions import ClientError
from fastapi import status
from pytest_mock import MockerFixture

from app.exceptions import PostNotPublishableException, PublishException
from app.models.post import Post
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService
from app.services.sshfs_storage_service import SSHFSStorageService
from app.settings import Settings

ERROR_MESSAGE: str = "error"


class TestPublisherService:
    def test_ssh_password_lookup_propagates_ssm_failure(
        self,
        mocker: MockerFixture,
        settings: Settings,
    ):
        ssm_error = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
            "GetParameter",
        )
        get_parameter = mocker.patch(
            "app.settings.parameters.get_parameter", side_effect=ssm_error
        )

        with pytest.raises(ClientError) as exc_info:
            _ = settings.ssh_password

        assert exc_info.value is ssm_error
        get_parameter.assert_called_once_with(
            settings._ssh_password_parameter_name, decrypt=True, max_age=60
        )

    def test_ssh_password_is_loaded_from_secure_parameter(
        self,
        mocker: MockerFixture,
        settings: Settings,
    ):
        get_parameter = mocker.patch(
            "app.settings.parameters.get_parameter", return_value="runtime-password"
        )

        assert settings.ssh_password == "runtime-password"
        get_parameter.assert_called_once_with(
            settings._ssh_password_parameter_name, decrypt=True, max_age=60
        )
        assert "ssh_password" not in settings.model_dump()

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
        update_state = mocker.patch.object(PostService, "update_publish_state")

        publisher_service.publish(posts[0].id)

        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()
        assert [call.args[1] for call in update_state.call_args_list] == [
            "publishing",
            "published",
        ]

    def test_publish_future_post(
        self,
        mocker: MockerFixture,
        post_service: PostService,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].published_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(SSHFSStorageService, "write")
        update_state = mocker.patch.object(PostService, "update_publish_state")

        with pytest.raises(PostNotPublishableException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.value.status_code == status.HTTP_409_CONFLICT
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_not_called()
        update_state.assert_not_called()

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
        update_state = mocker.patch.object(PostService, "update_publish_state")

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()
        assert [call.args[1] for call in update_state.call_args_list] == [
            "publishing",
            "failed",
        ]

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
        update_state = mocker.patch.object(PostService, "update_publish_state")

        with pytest.raises(PublishException) as excinfo:
            publisher_service.publish(posts[0].id)

        assert excinfo.typename == PublishException.__name__
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == ERROR_MESSAGE
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        sshfs_storage_service.write.assert_called_once()
        assert [call.args[1] for call in update_state.call_args_list] == [
            "publishing",
            "failed",
        ]

    def test_fail_to_publish_due_to_null_published_at(
        self,
        mocker: MockerFixture,
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
        mock_write = mocker.patch.object(SSHFSStorageService, "write")
        update_state = mocker.patch.object(PostService, "update_publish_state")

        with pytest.raises(PostNotPublishableException) as excinfo:
            publisher_service.publish(post.id)

        assert excinfo.value.status_code == status.HTTP_409_CONFLICT
        post_service.get_post_by_uuid.assert_called_once_with(post.id)
        mock_write.assert_not_called()
        update_state.assert_not_called()

    def test_remove_published_deletes_the_remote_file(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        publisher_service: PublisherService,
        settings: Settings,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].publish_status = "published"
        delete = mocker.patch.object(SSHFSStorageService, "delete")
        mocker.patch(
            "app.settings.parameters.get_parameter", return_value="runtime-password"
        )

        publisher_service.remove_published(posts[0])

        delete.assert_called_once_with(
            settings.ssh_host,
            settings.ssh_username,
            "runtime-password",
            f"{settings.ssh_root_path}/{posts[0].id}.md",
        )

    def test_remove_published_skips_posts_that_were_never_published(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].publish_status = None
        delete = mocker.patch.object(SSHFSStorageService, "delete")

        publisher_service.remove_published(posts[0])

        delete.assert_not_called()

    @pytest.mark.parametrize(
        "error",
        [SSHError(1, "ssh failed"), OSError("connection lost"), FileNotFoundError()],
    )
    def test_remove_published_does_not_raise_when_the_remote_fails(
        self,
        mocker: MockerFixture,
        error: Exception,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].publish_status = "published"
        mocker.patch.object(SSHFSStorageService, "delete", side_effect=error)
        mocker.patch(
            "app.settings.parameters.get_parameter", return_value="runtime-password"
        )

        publisher_service.remove_published(posts[0])

    def test_remove_published_does_not_raise_when_the_password_lookup_fails(
        self,
        mocker: MockerFixture,
        posts: list[Post],
        publisher_service: PublisherService,
        sshfs_storage_service: SSHFSStorageService,
    ):
        posts[0].publish_status = "published"
        delete = mocker.patch.object(SSHFSStorageService, "delete")
        mocker.patch(
            "app.settings.parameters.get_parameter", side_effect=RuntimeError("ssm")
        )

        publisher_service.remove_published(posts[0])

        delete.assert_not_called()
