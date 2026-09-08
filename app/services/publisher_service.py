import os
from datetime import UTC, datetime

from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger

from app.exceptions import PublishException
from app.services.post_service import PostService
from app.services.sshfs_storage_service import SSHFSStorageService
from app.settings import Settings as _Settings


class PublisherService:
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
        if post.published_at and datetime.fromisoformat(
            post.published_at
        ) < datetime.now(UTC):
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

    def _write(self, host: str, username: str, password: str, data: bytes, path: str):
        abs_path = os.path.join(self._settings.ssh_root_path, path)
        try:
            self._sshfs_storage_service.write(host, username, password, data, abs_path)
        except (SSHError, OSError) as e:
            self._logger.error("Failed to publish file", exc_info=e)
            raise PublishException(detail=str(e))
