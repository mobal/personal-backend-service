import pytest

from app.services.storage_service import StorageService

BUCKET_NAME = "test"
OBJECT_BODY = "This is a simple string."
OBJECT_KEY = "test"


@pytest.mark.asyncio
class TestStorageService:
    @pytest.fixture(autouse=True)
    def setup_function(self, s3_resource):
        s3_resource.create_bucket(
            ACL="public-read-write",
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": pytest.aws_default_region},
        )

    @pytest.fixture
    def storage_service(self) -> StorageService:
        return StorageService()

    async def test_successfully_create_bucket(
        self,
        s3_resource,
        storage_service: StorageService,
    ):
        bucket_name = "attachments"

        await storage_service.create_bucket(bucket_name)

        assert bucket_name in [bucket.name for bucket in s3_resource.buckets.all()]

    async def test_successfully_get_object(
        self,
        s3_resource,
        storage_service: StorageService,
    ):
        pass

    async def test_successfully_put_object(
        self,
        s3_resource,
        storage_service: StorageService,
    ):
        await storage_service.put_object(
            BUCKET_NAME, OBJECT_KEY, OBJECT_BODY.encode("utf-8")
        )

        obj = s3_resource.Object(s3_resource.Bucket(BUCKET_NAME).name, OBJECT_KEY)
        obj.load()
        response = obj.get()
        assert response["Body"].read().decode("utf-8") == OBJECT_BODY
