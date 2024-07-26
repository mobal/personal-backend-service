import boto3
from aws_lambda_powertools import Logger

from app import settings


class StorageService:
    def __init__(self):
        self.__logger = Logger(utc=True)
        self.__s3_client = boto3.client("s3")

    async def create_bucket(self, bucket: str, acl: str = "private"):
        self.__logger.info(f"Creating {bucket=} with {acl=}")
        self.__s3_client.create_bucket(
            ACL=acl,
            Bucket=bucket,
            CreateBucketConfiguration={
                "LocationConstraint": settings.aws_region,
            },
        )

    async def get_object(self, bucket: str, key: str):
        self.__logger.info(f"Get object {key=} from {bucket=}")
        response = self.__s3_client.get_object(
            Bucket=bucket,
            Key=key,
        )
        return response["Body"]

    async def get_object_attributes(self, bucket: str, key: str) -> dict:
        self.__logger.info(f"Get object attributes {key=} from {bucket=}")
        response = self.__s3_client.get_object_attributes(
            Bucket=bucket,
            Key=key,
        )
        return {
            "parts": response["ObjectParts"]["Parts"],
            "size": response["ObjectSize"],
        }

    async def list_objects(self, bucket: str) -> list:
        self.__logger.info(f"List {bucket=}")
        response = self.__s3_client.list_objects_v2(
            Bucket=bucket,
        )
        return response["Contents"]

    async def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        acl: str = "public-read",
        metadata: dict[str, str] | None = None,
    ):
        self.__logger.info(
            f"Put object with {key=} and {acl=} into {bucket=}", metadata=metadata
        )
        self.__s3_client.put_object(
            ACL=acl,
            Body=body,
            Bucket=bucket,
            Key=key,
            Metadata=metadata,
        )
