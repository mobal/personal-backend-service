import uuid

import pendulum
import pytest
from botocore.exceptions import ClientError
from fastapi import status

from app.services.storage_service import StorageService

BUCKET_NAME = "test"
OBJECT_BODY = "This is a simple string."
OBJECT_KEY = str(uuid.uuid4())


@pytest.mark.asyncio
class TestStorageService:
    @pytest.fixture(autouse=True)
    def setup_function(self, s3_resource):
        bucket = s3_resource.create_bucket(
            ACL="public-read-write",
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": pytest.aws_default_region},
        )
        s3_resource.Object(bucket.name, OBJECT_KEY).put(
            Body=OBJECT_BODY.encode("utf-8")
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

    async def test_successfully_delete_object(
        self,
        s3_resource,
        storage_service: StorageService,
    ):
        response = await storage_service.delete_object(BUCKET_NAME, OBJECT_KEY)

        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == status.HTTP_204_NO_CONTENT
        )

        with pytest.raises(ClientError) as exc_info:
            s3_resource.Object(bucket_name=BUCKET_NAME, key=OBJECT_KEY).get()
        assert issubclass(exc_info.type, ClientError)
        assert (
            str(exc_info.value)
            == "An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist."
        )

    async def test_successfully_get_object(
        self,
        storage_service: StorageService,
    ):
        response = await storage_service.get_object(BUCKET_NAME, OBJECT_KEY)

        assert response["Body"].read().decode("utf-8") == OBJECT_BODY

    async def test_successfully_list_objects(
        self,
        storage_service: StorageService,
    ):
        response = await storage_service.list_objects(BUCKET_NAME)
        objects = list(response)
        assert len(objects) == 1
        assert objects[0].get()["Body"].read().decode("utf-8") == OBJECT_BODY

    async def test_successfully_put_object(
        self,
        s3_resource,
        storage_service: StorageService,
    ):
        object_body = pendulum.now().to_iso8601_string()
        object_key = str(uuid.uuid4())

        await storage_service.put_object(
            BUCKET_NAME, object_key, object_body.encode("utf-8")
        )

        obj = s3_resource.Object(bucket_name=BUCKET_NAME, key=OBJECT_KEY)
        assert obj.get()["Body"].read().decode("utf-8") == OBJECT_BODY
