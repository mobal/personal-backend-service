from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from botocore.exceptions import ClientError

from app.exceptions import BucketNotFoundException, ObjectNotFoundException
from app.settings import Settings


class S3StorageService:
    def __init__(
        self,
        settings: Settings,
        region: str | None = None,
        retry_config: Config | None = None,
        logger: Logger | None = None,
    ):
        self._settings = settings
        self._logger = logger or Logger()
        resolved_region = region or self._settings.aws_region
        self._retry_config = retry_config or Config(
            retries={
                "max_attempts": 5,
                "mode": "adaptive",
            }
        )
        self._s3 = boto3.resource(
            "s3",
            region_name=resolved_region,
            config=self._retry_config,
        )
        self._region = resolved_region
        self._multipart_threshold = (
            8 * 1024 * 1024
        )  # 8MB threshold for multipart uploads
        self._s3_client = boto3.client(
            "s3",
            region_name=resolved_region,
            config=self._retry_config,
        )

    def create_bucket(self, bucket: str, acl: str = "private") -> dict[str, Any]:
        self._logger.info(f"Creating bucket={bucket} with acl={acl}")
        return self._s3.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": self._region},
        )

    def delete_object(self, bucket: str, key: str) -> dict[str, Any]:
        self._logger.info(f"Deleting object key={key} from bucket={bucket}")
        return self._s3.Object(bucket_name=bucket, key=key).delete()

    def get_bucket(self, name: str) -> dict[str, Any]:
        self._logger.info(f"Fetching bucket name={name}")
        bucket = self._s3.Bucket(name=name)
        if not bucket.creation_date:
            error = f"Bucket '{name}' not found"
            self._logger.error(error)
            raise BucketNotFoundException(error)
        return {"name": bucket.name, "creation_date": bucket.creation_date}

    def get_object(self, bucket: str, key: str) -> dict[str, Any]:
        self._logger.info(f"Fetching object key={key} from bucket={bucket}")
        obj = self._s3.Object(bucket_name=bucket, key=key)
        try:
            obj.load()
        except ClientError:
            error = f"Object key={key} not found in bucket={bucket}"
            self._logger.exception(error)
            raise ObjectNotFoundException(error)
        return obj.get()

    def list_objects(self, bucket: str) -> list[dict[str, Any]]:
        self._logger.info(f"Listing objects in bucket={bucket}")
        return [obj.get() for obj in self._s3.Bucket(name=bucket).objects.all()]

    def put_object(
        self, bucket: str, key: str, data: bytes, acl: str = "public-read"
    ) -> dict[str, Any]:
        self._logger.info(
            f"Uploading object key={key} with acl={acl} to bucket={bucket}"
        )
        return self._s3.Object(bucket_name=bucket, key=key).put(Body=data)

    def put_object_multipart(
        self,
        bucket: str,
        key: str,
        data: bytes,
        acl: str = "public-read",
        part_size: int = 5 * 1024 * 1024,  # 5MB parts
    ) -> dict[str, Any]:
        """Upload object using multipart upload for large files."""
        self._logger.info(
            f"Uploading object key={key} with acl={acl} to bucket={bucket} using multipart upload"
        )
        upload = self._s3_client.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            ACL=acl,
            ContentType="application/octet-stream",
        )
        upload_id = upload["UploadId"]

        parts = []
        try:
            total_parts = (len(data) + part_size - 1) // part_size
            for i, start in enumerate(range(0, len(data), part_size), start=1):
                end = start + part_size
                part_data = data[start:end]
                part_number = i

                part_response = self._s3_client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data,
                )
                parts.append(
                    {
                        "PartNumber": part_number,
                        "ETag": part_response["ETag"],
                    }
                )
                self._logger.debug(f"Uploaded part {part_number} of {total_parts}")

            complete_response = self._s3_client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            return complete_response
        except ClientError as exc:
            self._s3_client.abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
            )
            self._logger.exception(f"Multipart upload failed: {exc}")
            raise exc
