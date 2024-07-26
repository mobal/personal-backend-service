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

    async def get_object(self, bucket: str, key: str):
        self.__logger.info(f"Get object {key=} from {bucket=}")
        response = self.__s3_resource.get_object(
            Bucket=bucket,
            Key=key,
        )
        return response["Body"]

    async def get_object_attributes(self, bucket: str, key: str) -> dict:
        self.__logger.info(f"Get object attributes {key=} from {bucket=}")
        response = self.__s3_resource.get_object_attributes(
            Bucket=bucket,
            Key=key,
        )
        return {
            "parts": response["ObjectParts"]["Parts"],
            "size": response["ObjectSize"],
        }

    async def list_objects(self, bucket: str) -> list:
        self.__logger.info(f"List {bucket=}")
        response = self.__s3_resource.list_objects_v2(
            Bucket=bucket,
        )
        return response["Contents"]

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
