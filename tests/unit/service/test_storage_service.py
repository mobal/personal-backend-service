import boto3
import pytest
from moto import mock_aws

from app.services.storage_service import StorageService


@pytest.mark.asyncio
class TestStorageService:
    @pytest.fixture
    def storage_service(self) -> StorageService:
        return StorageService()

    async def test_successfully_create_bucket(
        self,
        storage_service: StorageService,
    ):
        bucket = "test-attachments"
        with mock_aws():
            await storage_service.create_bucket(bucket)

            s3_client = boto3.client("s3")
            response = s3_client.list_buckets()
            assert bucket in response["Buckets"][0]["Name"]
