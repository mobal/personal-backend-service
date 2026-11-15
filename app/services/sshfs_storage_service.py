from builtins import list as builtin_list
from collections.abc import Generator
from contextlib import contextmanager

from asyncssh import (
    Error as SSHError,
    import_known_hosts,
)
from aws_lambda_powertools import Logger
from sshfs import SSHFileSystem


class SSHFSStorageService:
    # Fail well inside the Lambda timeout when the remote host is unreachable.
    CONNECT_TIMEOUT_SECONDS = 5

    def __init__(self, known_hosts: str | None = None):
        """known_hosts: trusted host keys in OpenSSH known_hosts format."""
        self._logger = Logger()
        self._known_hosts = import_known_hosts(known_hosts) if known_hosts else None

    @contextmanager
    def _fs(self, host: str, username: str, password: str) -> Generator[SSHFileSystem]:
        if self._known_hosts is None:
            # sshfs disables host key checks unless known_hosts is passed.
            self._logger.warning(
                "SSH host key verification is disabled; set SSH_KNOWN_HOSTS"
            )
        fs = SSHFileSystem(
            host,
            username=username,
            password=password,
            known_hosts=self._known_hosts,
            connect_timeout=self.CONNECT_TIMEOUT_SECONDS,
            login_timeout=self.CONNECT_TIMEOUT_SECONDS,
            # fsspec caches instances by their arguments; a cached instance
            # would come back with the client that was closed below.
            skip_instance_cache=True,
        )
        try:
            yield fs
        finally:
            fs.client.close()

    def delete(self, host: str, username: str, password: str, path: str):
        try:
            with self._fs(host, username, password) as fs:
                fs.rm(path)
        except SSHError, OSError:
            self._logger.exception("Failed to delete file", extra={"path": path})
            raise

    def download(self, host: str, username: str, password: str, path: str) -> bytes:
        try:
            with self._fs(host, username, password) as fs:
                with fs.open(path, "rb") as f:
                    return f.read()
        except SSHError, OSError:
            self._logger.exception("Failed to download file", extra={"path": path})
            raise

    def exists(self, host: str, username: str, password: str, path: str) -> bool:
        try:
            with self._fs(host, username, password) as fs:
                return fs.exists(path)
        except SSHError, OSError:
            self._logger.exception(
                "Failed to check file existence", extra={"path": path}
            )
            raise

    def list(
        self, host: str, username: str, password: str, path: str
    ) -> builtin_list[str]:
        try:
            with self._fs(host, username, password) as fs:
                return fs.ls(path)
        except SSHError, OSError:
            self._logger.exception("Failed to list files", extra={"path": path})
            raise

    def write(self, host: str, username: str, password: str, data: bytes, path: str):
        try:
            with self._fs(host, username, password) as fs:
                with fs.open(path, "wb") as f:
                    f.write(data)
        except SSHError, OSError:
            self._logger.exception("Failed to write file", extra={"path": path})
            raise
