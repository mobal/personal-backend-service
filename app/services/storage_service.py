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
        self._s3 = boto3.resource("s3", region_name=settings.aws_region)

    def create_bucket(self, bucket: str, acl: BucketCannedACLType = "private") -> Bucket:
        self._logger.info(f"Creating bucket={bucket} with acl={acl}")
        return self._s3.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": settings.aws_region},
        )

    def delete_object(self, bucket: str, key: str) -> dict[str, Any]:
        self._logger.info(f"Deleting object key={key} from bucket={bucket}")
        return self._s3.Object(bucket_name=bucket, key=key).delete()

    def get_bucket(self, name: str) -> Bucket:
        self._logger.info(f"Fetching bucket name={name}")
        bucket = self._s3.Bucket(name=name)
        if not bucket.creation_date:
            error = f"Bucket '{name}' not found"
            self._logger.error(error)
            raise BucketNotFoundException(error)
        return bucket

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

    def list_objects(self, bucket: str) -> BucketObjectsCollection:
        self._logger.info(f"Listing objects in bucket={bucket}")
        return self._s3.Bucket(name=bucket).objects.all()

    def put_object(self, bucket: str, key: str, data: bytes, acl: str = "public-read") -> dict[str, Any]:
        self._logger.info(f"Uploading object key={key} with acl={acl} to bucket={bucket}")
        return self._s3.Object(bucket_name=bucket, key=key).put(Body=data)
