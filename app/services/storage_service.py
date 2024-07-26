import boto3
from aws_lambda_powertools import Logger

from app import settings


class StorageService:
    def __init__(self):
        self.__logger = Logger(utc=True)
        self.__s3_resource = boto3.resource("s3", region_name=settings.aws_region)

    async def create_bucket(self, bucket: str, acl: str = "private"):
        self.__logger.info(f"Creating {bucket=} with {acl=}")
        self.__s3_resource.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": settings.aws_region,
            },
        )

    async def delete_object(self, bucket: str, key: str):
        self.__logger.info(f"Delete object {key=} from {bucket=}")
        return self.__s3_resource.Object(bucket_name=bucket, key=key).delete()

    async def get_object(self, bucket: str, key: str):
        self.__logger.info(f"Get object {key=} from {bucket=}")
        return self.__s3_resource.Object(bucket_name=bucket, key=key).get()

    async def list_objects(self, bucket: str) -> list:
        self.__logger.info(f"Listing {bucket=}")
        return self.__s3_resource.Bucket(name=bucket).objects.all()

    async def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        acl: str = "public-read",
        metadata: dict[str, str] = {},
    ):
        self.__logger.info(
            f"Put object with {key=} and {acl=} into {bucket=}", metadata=metadata
        )
        self.__s3_resource.Object(bucket_name=bucket, key=key).put(
            Body=body, Metadata=metadata
        )
