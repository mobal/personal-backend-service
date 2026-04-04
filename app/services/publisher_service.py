import os

import pendulum
from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger

from app import Settings
from app.exceptions import PublishException
from app.services.post_service import PostService
from app.services.sshfs_storage_service import SSHFSStorageService


class PublisherService:
    def __init__(self):
        self._logger = Logger()
        self._post_service = PostService()
        self._settings = Settings()
        self._sshfs_storage_service = SSHFSStorageService()

    def publish(self, post_uuid: str) -> None:
        self._logger.info(f"Publishing post with id={post_uuid}")
        post = self._post_service.get_post_by_uuid(post_uuid)
        if pendulum.parse(post.published_at).is_past():
            self._write(
                self._settings.ssh_host,
                self._settings.ssh_username,
                self._settings.ssh_password,
                post.content.encode("utf-8"),
                f"{post.id}.md",
            )

    def _write(self, host: str, username: str, password: str, data: bytes, path: str):
        abs_path = os.path.join(self._settings.ssh_root_path, path)
        try:
            self._sshfs_storage_service.write(host, username, password, data, abs_path)
        except (SSHError, OSError) as e:
            self._logger.error("Failed to publish file", exc_info=e)
            raise PublishException(detail=str(e))
