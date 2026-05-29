import uuid

import pendulum
import pytest
from botocore.exceptions import ClientError
from fastapi import status

from app.exceptions import BucketNotFoundException, ObjectNotFoundException
from app.services.s3_storage_service import S3StorageService

BUCKET_NAME = "test"
OBJECT_BODY = "This is a simple string."
OBJECT_KEY = str(uuid.uuid4())


class TestS3StorageService:
    @pytest.fixture(autouse=True)
    def setup_function(self, aws_default_region: str, s3_resource):
        bucket = s3_resource.create_bucket(
            ACL="public-read-write",
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": aws_default_region},
        )
        s3_resource.Object(bucket.name, OBJECT_KEY).put(
            Body=OBJECT_BODY.encode("utf-8")
        )

    def test_successfully_create_bucket(
        self,
        s3_resource,
        s3_storage_service: S3StorageService,
    ):
        bucket_name = "attachments"

        s3_storage_service.create_bucket(bucket_name)

        assert bucket_name in [bucket.name for bucket in s3_resource.buckets.all()]

    def test_fail_to_create_bucket_due_to_already_exists(
        self,
        s3_storage_service: S3StorageService,
        mocker,
    ):
        client_error = ClientError(
            {
                "Error": {
                    "Code": "BucketAlreadyOwnedByYou",
                    "Message": "Your previous request to create the named bucket succeeded and you already own it.",
                }
            },
            "CreateBucket",
        )
        mocker.patch.object(
            s3_storage_service._s3, "create_bucket", side_effect=client_error
        )

        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.create_bucket("test-bucket")

        assert exc_info.value.response["Error"]["Code"] == "BucketAlreadyOwnedByYou"

    def test_successfully_delete_object(
        self,
        s3_resource,
        s3_storage_service: S3StorageService,
    ):
        response = s3_storage_service.delete_object(BUCKET_NAME, OBJECT_KEY)

        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == status.HTTP_204_NO_CONTENT
        )

        with pytest.raises(ClientError) as exc_info:
            s3_resource.Object(bucket_name=BUCKET_NAME, key=OBJECT_KEY).get()
        assert issubclass(exc_info.type, ClientError)
        assert (
            str(exc_info.value)
            == "An error occurred (NoSuchKey) when calling the GetObject operation: "
            "The specified key does not exist."
        )

    def test_successfully_get_bucket(self, s3_storage_service: S3StorageService):
        response = s3_storage_service.get_bucket(BUCKET_NAME)

        assert response["creation_date"]
        assert response["name"] == BUCKET_NAME

    def test_fail_to_get_bucket_due_to_not_found(
        self, s3_storage_service: S3StorageService
    ):
        with pytest.raises(BucketNotFoundException) as exc_info:
            s3_storage_service.get_bucket("invalid")

        assert exc_info.type == BucketNotFoundException
        assert exc_info.value.detail == "Bucket 'invalid' not found"

    def test_successfully_get_object(
        self,
        s3_storage_service: S3StorageService,
    ):
        response = s3_storage_service.get_object(BUCKET_NAME, OBJECT_KEY)

        assert response["Body"].read().decode("utf-8") == OBJECT_BODY

    def test_fail_to_get_object_due_to_not_found(
        self, s3_storage_service: S3StorageService
    ):
        with pytest.raises(ObjectNotFoundException) as exc_info:
            s3_storage_service.get_object(BUCKET_NAME, "invalid")

        assert exc_info.type == ObjectNotFoundException
        assert (
            exc_info.value.detail
            == f"Object key=invalid not found in bucket={BUCKET_NAME}"
        )

    def test_fail_to_get_object_due_to_race_condition(
        self,
        s3_storage_service: S3StorageService,
        mocker,
    ):
        client_error = ClientError(
            {
                "Error": {
                    "Code": "NoSuchKey",
                    "Message": "The specified key does not exist.",
                }
            },
            "GetObject",
        )
        mock_obj = mocker.Mock()
        mock_obj.load.return_value = None
        mock_obj.get.side_effect = client_error
        mocker.patch.object(s3_storage_service._s3, "Object", return_value=mock_obj)

        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.get_object(BUCKET_NAME, OBJECT_KEY)

        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_successfully_list_objects(
        self,
        s3_storage_service: S3StorageService,
    ):
        response = s3_storage_service.list_objects(BUCKET_NAME)
        objects = list(response)
        assert len(objects) == 1
        assert objects[0]["Body"].read().decode("utf-8") == OBJECT_BODY

    def test_fail_to_list_objects_due_to_non_existent_bucket(
        self,
        s3_storage_service: S3StorageService,
    ):
        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.list_objects("non-existent-bucket")

        assert exc_info.value.response["Error"]["Code"] == "NoSuchBucket"

    def test_successfully_put_object(
        self,
        s3_resource,
        s3_storage_service: S3StorageService,
    ):
        object_body = pendulum.now().to_iso8601_string()
        object_key = str(uuid.uuid4())

        s3_storage_service.put_object(
            BUCKET_NAME, object_key, object_body.encode("utf-8")
        )

        obj = s3_resource.Object(bucket_name=BUCKET_NAME, key=OBJECT_KEY)
        assert obj.get()["Body"].read().decode("utf-8") == OBJECT_BODY

    def test_fail_to_put_object_due_to_non_existent_bucket(
        self,
        s3_storage_service: S3StorageService,
    ):
        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.put_object("non-existent-bucket", "key", b"data")

        assert exc_info.value.response["Error"]["Code"] == "NoSuchBucket"

    def test_fail_to_put_object_due_to_client_error(
        self,
        s3_storage_service: S3StorageService,
        mocker,
    ):
        client_error = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Upload failed"}},
            "PutObject",
        )
        mock_obj = mocker.Mock()
        mock_obj.put.side_effect = client_error
        mocker.patch.object(s3_storage_service._s3, "Object", return_value=mock_obj)

        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.put_object(BUCKET_NAME, "key", b"data")

        assert exc_info.value.response["Error"]["Code"] == "InternalError"

    def test_successfully_put_object_multipart(
        self,
        s3_resource,
        s3_storage_service: S3StorageService,
    ):
        part_size = 5 * 1024 * 1024
        object_body = (b"a" * part_size) + b"last part"
        object_key = str(uuid.uuid4())

        response = s3_storage_service.put_object_multipart(
            BUCKET_NAME, object_key, object_body, part_size=part_size
        )

        obj = s3_resource.Object(bucket_name=BUCKET_NAME, key=object_key)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == status.HTTP_200_OK
        assert obj.get()["Body"].read() == object_body

    def test_abort_put_object_multipart_on_client_error(
        self,
        s3_storage_service: S3StorageService,
        mocker,
    ):
        upload_id = str(uuid.uuid4())
        object_key = str(uuid.uuid4())
        client_error = ClientError(
            {
                "Error": {
                    "Code": "InternalError",
                    "Message": "Upload failed",
                },
            },
            "UploadPart",
        )
        s3_client = mocker.Mock()
        s3_client.create_multipart_upload.return_value = {"UploadId": upload_id}
        s3_client.upload_part.side_effect = client_error
        s3_storage_service._s3_client = s3_client

        with pytest.raises(ClientError) as exc_info:
            s3_storage_service.put_object_multipart(
                BUCKET_NAME, object_key, b"failed upload", part_size=5
            )

        assert exc_info.value == client_error
        s3_client.abort_multipart_upload.assert_called_once_with(
            Bucket=BUCKET_NAME,
            Key=object_key,
            UploadId=upload_id,
        )
