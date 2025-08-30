from unittest.mock import MagicMock, call, mock_open

import pytest
from asyncssh import Error as SSHError
from pytest_mock import MockerFixture

from app.services.sshfs_storage_service import SSHFSStorageService


class TestSSHFSStorageService:
    @pytest.fixture
    def mock_fs(self):
        return MagicMock()

    @pytest.fixture
    def mock_sshfs(self, mocker: MockerFixture):
        return mocker.patch("app.services.sshfs_storage_service.SSHFileSystem")

    def test_successfully_download(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"test content"
        mock_fs.open.return_value.__enter__.return_value = mock_stream
        
        result = sshfs_storage_service.download("localhost", "username", "password", "/path/to/file")

        assert result == b"test content"
        mock_fs.open.assert_called_once_with("/path/to/file", "rb")
        mock_stream.read.assert_called_once()
        mock_fs.client.close.assert_called_once()

    def test_fail_to_download_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.open.side_effect = SSHError(1, "SSH error")

        with pytest.raises(SSHError):
            sshfs_storage_service.download("localhost", "username", "password", "/path/to/file")

        mock_fs.open.assert_called_once_with("/path/to/file", "rb")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_download_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.open.side_effect = OSError("OS error")

        with pytest.raises(OSError):
            sshfs_storage_service.download("localhost", "username", "password", "/path/to/file")

        mock_fs.open.assert_called_once_with("/path/to/file", "rb")
        mock_fs.client.close.assert_called_once()

    def test_successfully_write(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_stream = MagicMock()
        mock_fs.open.return_value.__enter__.return_value = mock_stream
        test_data = b"test data to write"
        
        sshfs_storage_service.write("localhost", "username", "password", test_data, "/path/to/file")

        mock_fs.open.assert_called_once_with("/path/to/file", "wb")
        mock_stream.write.assert_called_once_with(test_data)
        mock_fs.client.close.assert_called_once()

    def test_fail_to_write_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.open.side_effect = SSHError(2, "SSH connection failed")

        with pytest.raises(SSHError):
            sshfs_storage_service.write("localhost", "username", "password", b"data", "/path/to/file")

        mock_fs.open.assert_called_once_with("/path/to/file", "wb")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_write_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.open.side_effect = OSError("Permission denied")

        with pytest.raises(OSError):
            sshfs_storage_service.write("localhost", "username", "password", b"data", "/path/to/file")

        mock_fs.client.close.assert_called_once()

    def test_successfully_delete(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        
        sshfs_storage_service.delete("localhost", "username", "password", "/path/to/file")

        mock_fs.rm.assert_called_once_with("/path/to/file")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_delete_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.rm.side_effect = SSHError(3, "File not found")

        with pytest.raises(SSHError):
            sshfs_storage_service.delete("localhost", "username", "password", "/path/to/file")

        mock_fs.rm.assert_called_once_with("/path/to/file")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_delete_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.rm.side_effect = OSError("Access denied")

        with pytest.raises(OSError):
            sshfs_storage_service.delete("localhost", "username", "password", "/path/to/file")

        mock_fs.client.close.assert_called_once()

    def test_file_exists(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.exists.return_value = True
        
        result = sshfs_storage_service.exists("localhost", "username", "password", "/path/to/file")

        assert result is True
        mock_fs.exists.assert_called_once_with("/path/to/file")
        mock_fs.client.close.assert_called_once()

    def test_file_does_not_exist(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.exists.return_value = False
        
        result = sshfs_storage_service.exists("localhost", "username", "password", "/path/to/file")

        assert result is False
        mock_fs.exists.assert_called_once_with("/path/to/file")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_check_existence_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.exists.side_effect = SSHError(4, "Connection timeout")

        with pytest.raises(SSHError):
            sshfs_storage_service.exists("localhost", "username", "password", "/path/to/file")

        mock_fs.client.close.assert_called_once()

    def test_fail_to_check_existence_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.exists.side_effect = OSError("Network unreachable")

        with pytest.raises(OSError):
            sshfs_storage_service.exists("localhost", "username", "password", "/path/to/file")

        mock_fs.client.close.assert_called_once()

    def test_successfully_list_files(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        expected_files = ["file1.txt", "file2.txt", "subdir/"]
        mock_fs.ls.return_value = expected_files
        
        result = sshfs_storage_service.list("localhost", "username", "password", "/path/to/dir")

        assert result == expected_files
        mock_fs.ls.assert_called_once_with("/path/to/dir")
        mock_fs.client.close.assert_called_once()

    def test_successfully_list_empty_directory(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.ls.return_value = []
        
        result = sshfs_storage_service.list("localhost", "username", "password", "/empty/dir")

        assert result == []
        mock_fs.ls.assert_called_once_with("/empty/dir")
        mock_fs.client.close.assert_called_once()

    def test_fail_to_list_due_to_ssh_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.ls.side_effect = SSHError(5, "Directory not found")

        with pytest.raises(SSHError):
            sshfs_storage_service.list("localhost", "username", "password", "/nonexistent/dir")

        mock_fs.client.close.assert_called_once()

    def test_fail_to_list_due_to_os_error(
        self,
        mock_fs: MagicMock,
        mock_sshfs: MagicMock,
        sshfs_storage_service: SSHFSStorageService,
    ):
        mock_sshfs.return_value = mock_fs
        mock_fs.ls.side_effect = OSError("Permission denied")

        with pytest.raises(OSError):
            sshfs_storage_service.list("localhost", "username", "password", "/restricted/dir")

        mock_fs.client.close.assert_called_once()
