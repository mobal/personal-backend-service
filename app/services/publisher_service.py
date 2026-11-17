import os
from datetime import UTC, datetime

from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger

from app.exceptions import PostNotPublishableException, PublishException
from app.models.post import Post
from app.services.post_service import PostService
from app.services.sshfs_storage_service import SSHFSStorageService
from app.settings import Settings as _Settings


class PublisherService:
    ERROR_NOT_PUBLISHABLE = "The post has no publication date in the past"

    def __init__(
        self,
        post_service: PostService,
        storage_service: SSHFSStorageService,
        settings: _Settings,
    ):
        self._logger = Logger()
        self._settings = settings
        self._post_service = post_service
        self._sshfs_storage_service = storage_service

    def publish(self, post_uuid: str) -> None:
        self._logger.info(f"Publishing post with id={post_uuid}")
        post = self._post_service.get_post_by_uuid(post_uuid)
        if not post.published_at or datetime.fromisoformat(
            post.published_at
        ) > datetime.now(UTC):
            raise PostNotPublishableException(self.ERROR_NOT_PUBLISHABLE)

        attempted_at = datetime.now(UTC).isoformat()
        self._post_service.update_publish_state(post.id, "publishing", attempted_at)
        try:
            self._write(
                self._settings.ssh_host,
                self._settings.ssh_username,
                self._settings.ssh_password,
                post.content.encode("utf-8"),
                f"{post.id}.md",
            )
        except PublishException as exc:
            self._post_service.update_publish_state(
                post.id, "failed", attempted_at, str(exc.detail)
            )
            raise
        self._post_service.update_publish_state(post.id, "published", attempted_at)

    def remove_published(self, post: Post) -> None:
        """Remove the published file of a deleted post; failures are only logged.

        Posts that were never published have no file, so the remote server is
        not contacted for them. The post is already soft-deleted when this
        runs, so an unreachable server must not fail the request.
        """
        if not post.publish_status:
            return
        path = os.path.join(self._settings.ssh_root_path, f"{post.id}.md")
        try:
            self._sshfs_storage_service.delete(
                self._settings.ssh_host,
                self._settings.ssh_username,
                self._settings.ssh_password,
                path,
            )
        except FileNotFoundError:
            self._logger.info(f"Published file of {post.id=} was already gone")
        except Exception as error:
            self._logger.error(
                f"Failed to delete the published file of {post.id=}: {error}"
            )

    def _write(self, host: str, username: str, password: str, data: bytes, path: str):
        abs_path = os.path.join(self._settings.ssh_root_path, path)
        try:
            self._sshfs_storage_service.write(host, username, password, data, abs_path)
        except (SSHError, OSError) as e:
            self._logger.error("Failed to publish file", exc_info=e)
            raise PublishException(detail=str(e))
