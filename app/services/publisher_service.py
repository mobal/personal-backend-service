import os
import pendulum
from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger
from sshfs import SSHFileSystem
from app import Settings
from app.exceptions import PublishException
from app.services.post_service import PostService


class PublisherService:
    def __init__(self):
        self._logger = Logger(utc=True)
        self._post_service = PostService()
        self._settings = Settings()

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

    def rm(self, path: str):
        fs = SSHFileSystem(
            self._settings.ssh_host,
            username=self._settings.ssh_username,
            password=self._settings.ssh_password,
        )
        try:
            fs.rm(path)
        except (SSHError, OSError) as e:
            self._logger.error(e)
            raise PublishException(detail=str(e))

    def _write(self, host: str, username: str, password: str, data: bytes, path: str):
        fs = SSHFileSystem(host, username=username, password=password)
        abs_path = os.path.join(self._settings.ssh_root_path, path)
        try:
            with fs.open(abs_path, "wb") as stream:
                stream.write(data)
        except (SSHError, OSError) as e:
            self._logger.error(e)
            raise PublishException(detail=str(e))
