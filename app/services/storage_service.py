from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from mypy_boto3_s3.literals import BucketCannedACLType
from mypy_boto3_s3.service_resource import Bucket, BucketObjectsCollection

from app import settings
from app.exceptions import BucketNotFoundException, ObjectNotFoundException


class StorageService:
    def __init__(self):
        self._logger = Logger(utc=True)
        self._s3_resource = boto3.resource("s3", region_name=settings.aws_region)

    def create_bucket(
        self, bucket: str, acl: BucketCannedACLType = "private"
    ) -> Bucket:
        self._logger.info(f"Creating {bucket=} with {acl=}")
        return self._s3_resource.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": settings.aws_region,
            },
        )

    def delete_object(self, bucket: str, key: str) -> dict[str, Any]:
        self._logger.info(f"Delete object {key=} from {bucket=}")
        return self._s3_resource.Object(bucket_name=bucket, key=key).delete()

    def get_bucket(self, name: str) -> Bucket:
        self._logger.info(f"Get bucket {name=}")
        bucket = self._s3_resource.Bucket(name=name)
        if bucket.creation_date is None:
            error_message = f"The requested bucket='{name}' was not found"
            self._logger.error(error_message)
            raise BucketNotFoundException(error_message)
        return bucket

    def get_object(self, bucket: str, key: str) -> dict[str, Any]:
        self._logger.info(f"Get object {key=} from {bucket=}")
        obj = self._s3_resource.Object(bucket_name=bucket, key=key)
        try:
            obj.load()
        except ClientError:
            error_message = f"Failed to load object from {bucket=} with {key=}"
            self._logger.exception(error_message)
            raise ObjectNotFoundException(error_message)
        return obj.get()

    def list_objects(self, bucket: str) -> BucketObjectsCollection:
        self._logger.info(f"Listing {bucket=}")
        return self._s3_resource.Bucket(name=bucket).objects.all()

    def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        acl: str = "public-read",
    ) -> dict[str, Any]:
        self._logger.info(f"Put object with {key=} and {acl=} into {bucket=}")
        return self._s3_resource.Object(bucket_name=bucket, key=key).put(Body=data)
