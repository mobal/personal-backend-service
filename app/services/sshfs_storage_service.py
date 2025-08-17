from contextlib import contextmanager
from typing import Generator

from asyncssh import Error as SSHError
from aws_lambda_powertools import Logger
from sshfs import SSHFileSystem


class SSHFSStorageService:
    def __init__(self):
        self._logger = Logger(utc=True)

    @contextmanager
    def _fs(
        self, host: str, username: str, password: str
    ) -> Generator[SSHFileSystem, None, None]:
        fs = SSHFileSystem(host, username=username, password=password)
        try:
            yield fs
        except (SSHError, OSError) as err:
            self._logger.exception(err)
            raise
        finally:
            fs.client.close()

    def delete(self, host: str, username: str, password: str, path: str):
        with self._fs(host, username, password) as fs:
            fs.rm(path)

    def download(self, host: str, username: str, password: str, path: str) -> bytes:
        with self._fs(host, username, password) as fs:
            with fs.open(path, "rb") as f:
                return f.read()

    def exists(self, host: str, username: str, password: str, path: str) -> bool:
        with self._fs(host, username, password) as fs:
            return fs.exists(path)

    def list(self, host: str, username: str, password: str, path: str) -> list[str]:
        with self._fs(host, username, password) as fs:
            return fs.ls(path)

    def write(self, host: str, username: str, password: str, data: bytes, path: str):
        with self._fs(host, username, password) as fs:
            with fs.open(path, "wb") as f:
                f.write(data)
