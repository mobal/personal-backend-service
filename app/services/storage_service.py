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
        self.__logger = Logger(utc=True)
        self.__s3_resource = boto3.resource("s3", region_name=settings.aws_region)

    async def create_bucket(
        self, bucket: str, acl: BucketCannedACLType = "private"
    ) -> Bucket:
        self.__logger.info(f"Creating {bucket=} with {acl=}")
        return self.__s3_resource.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": settings.aws_region,
            },
        )

    async def delete_object(self, bucket: str, key: str) -> dict[str, Any]:
        self.__logger.info(f"Delete object {key=} from {bucket=}")
        return self.__s3_resource.Object(bucket_name=bucket, key=key).delete()

    async def get_bucket(self, name: str) -> Bucket:
        self.__logger.info(f"Get bucket {name=}")
        bucket = self.__s3_resource.Bucket(name=name)
        if bucket.creation_date is None:
            error_message = f"The requested bucket='{name}' was not found"
            self.__logger.error(error_message)
            raise BucketNotFoundException(error_message)
        return bucket

    async def get_object(self, bucket: str, key: str) -> dict[str, Any]:
        self.__logger.info(f"Get object {key=} from {bucket=}")
        obj = self.__s3_resource.Object(bucket_name=bucket, key=key)
        try:
            obj.load()
        except ClientError:
            error_message = f"Failed to load object from {bucket=} with {key=}"
            self.__logger.exception(error_message)
            raise ObjectNotFoundException(error_message)
        return obj.get()

    async def list_objects(self, bucket: str) -> BucketObjectsCollection:
        self.__logger.info(f"Listing {bucket=}")
        return self.__s3_resource.Bucket(name=bucket).objects.all()

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        acl: str = "public-read",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if metadata is None:
            metadata = {}
        self.__logger.info(
            f"Put object with {key=} and {acl=} into {bucket=}", metadata=metadata
        )
        return self.__s3_resource.Object(bucket_name=bucket, key=key).put(
            Body=data, Metadata=metadata
        )
