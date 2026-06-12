from collections.abc import Generator
from contextlib import contextmanager

from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger
from sshfs import SSHFileSystem


class SSHFSStorageService:
    def __init__(self):
        self._logger = Logger()

    @contextmanager
    def _fs(self, host: str, username: str, password: str) -> Generator[SSHFileSystem]:
        fs = SSHFileSystem(host, username=username, password=password)
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

    def list(self, host: str, username: str, password: str, path: str) -> list[str]:
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
