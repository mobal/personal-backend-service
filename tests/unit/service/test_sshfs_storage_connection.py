"""Exercise SSHFSStorageService against a real in-process SFTP server.

Connection reuse and host key checks live in sshfs/asyncssh, so a mocked
SSHFileSystem cannot catch regressions in how the service configures them.
"""

import asyncio
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import asyncssh
import pytest
from pytest_mock import MockerFixture
from sshfs import SSHFileSystem

from app.services.sshfs_storage_service import SSHFSStorageService

USERNAME = "publisher"
PASSWORD = "test-only-password"


@dataclass
class SFTPServer:
    port: int
    root: Path
    host_key: asyncssh.SSHKey

    def known_hosts(self, key: asyncssh.SSHKey | None = None) -> str:
        public_key = (key or self.host_key).export_public_key().decode().strip()
        return f"[127.0.0.1]:{self.port} {public_key}\n"


class _PasswordServer(asyncssh.SSHServer):
    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        return username == USERNAME and password == PASSWORD


@pytest.fixture
def sftp_server(tmp_path: Path, mocker: MockerFixture) -> Iterator[SFTPServer]:
    host_key = asyncssh.generate_private_key("ssh-ed25519")
    loop = asyncio.new_event_loop()
    started = threading.Event()
    port = 0

    async def serve() -> None:
        nonlocal port
        server = await asyncssh.create_server(
            _PasswordServer,
            "127.0.0.1",
            0,
            server_host_keys=[host_key],
            sftp_factory=lambda chan: asyncssh.SFTPServer(
                chan, chroot=str(tmp_path).encode()
            ),
        )
        port = server.sockets[0].getsockname()[1]
        started.set()

    def run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(serve())
        loop.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert started.wait(timeout=10)

    # The service connects to the default SSH port; point it at the test server.
    mocker.patch(
        "app.services.sshfs_storage_service.SSHFileSystem",
        side_effect=lambda host, **kwargs: SSHFileSystem(host, port=port, **kwargs),
    )
    yield SFTPServer(port=port, root=tmp_path, host_key=host_key)
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)


class TestSSHFSStorageConnection:
    def test_consecutive_writes_each_get_a_working_connection(
        self, sftp_server: SFTPServer
    ):
        service = SSHFSStorageService(known_hosts=sftp_server.known_hosts())

        for name in ("first.md", "second.md"):
            service.write("127.0.0.1", USERNAME, PASSWORD, b"content", f"/{name}")

        assert (sftp_server.root / "first.md").read_bytes() == b"content"
        assert (sftp_server.root / "second.md").read_bytes() == b"content"

    def test_write_is_refused_when_the_host_key_does_not_match(
        self, sftp_server: SFTPServer
    ):
        other_key = asyncssh.generate_private_key("ssh-ed25519")
        service = SSHFSStorageService(known_hosts=sftp_server.known_hosts(other_key))

        with pytest.raises(asyncssh.HostKeyNotVerifiable):
            service.write("127.0.0.1", USERNAME, PASSWORD, b"content", "/post.md")

        assert not (sftp_server.root / "post.md").exists()

    def test_write_without_pinned_host_key_still_connects(
        self, sftp_server: SFTPServer
    ):
        service = SSHFSStorageService()

        service.write("127.0.0.1", USERNAME, PASSWORD, b"content", "/post.md")

        assert (sftp_server.root / "post.md").read_bytes() == b"content"
