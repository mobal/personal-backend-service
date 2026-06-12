import uuid

import boto3
import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, ConditionBase

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken
from app.repositories.post_repository import PostRepository
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService
from app.services.rate_limiter_service import RateLimiterService
from app.services.s3_storage_service import S3StorageService
from app.services.sshfs_storage_service import SSHFSStorageService
from app.settings import Settings


@pytest.fixture
def attachment_service(
    post_service: PostService,
    s3_storage_service: S3StorageService,
    settings: Settings,
) -> AttachmentService:
    return AttachmentService(
        settings=settings,
        post_service=post_service,
        storage_service=s3_storage_service,
    )


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer(jwt_secret=Settings().jwt_secret)


@pytest.fixture
def filter_expression() -> ConditionBase:
    return Attr("deleted_at").eq(None) & Attr("published_at").ne(None)


@pytest.fixture
def jwt_token(user_dict: dict[str, str | None]) -> JWTToken:
    now = pendulum.now()
    return JWTToken(
        exp=now.add(years=1).int_timestamp,
        iat=now.int_timestamp,
        iss="https://netcode.hu",
        jti=str(uuid.uuid4()),
        sub=user_dict["id"],
        user=user_dict,
    )


@pytest.fixture
def post_repository(
    initialize_posts_table, dynamodb_resource, settings: Settings
) -> PostRepository:
    return PostRepository(
        table_name=f"{settings.stage}-posts",
        db=dynamodb_resource,
    )


@pytest.fixture
def post_service(post_repository: PostRepository) -> PostService:
    return PostService(post_repository=post_repository)


@pytest.fixture
def publisher_service(
    post_service: PostService,
    sshfs_storage_service: SSHFSStorageService,
    settings: Settings,
) -> PublisherService:
    return PublisherService(
        post_service=post_service,
        storage_service=sshfs_storage_service,
        settings=settings,
    )


@pytest.fixture
def s3_storage_service(aws_default_region: str) -> S3StorageService:
    return S3StorageService(region=aws_default_region)


@pytest.fixture
def sshfs_storage_service() -> SSHFSStorageService:
    return SSHFSStorageService()


@pytest.fixture
def initialize_rate_limits_table(aws_default_region: str):
    client = boto3.client("dynamodb", region_name=aws_default_region)
    client.create_table(
        TableName="test-rate-limits",
        KeySchema=[
            {"AttributeName": "client_id", "KeyType": "HASH"},
            {"AttributeName": "endpoint", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "client_id", "AttributeType": "S"},
            {"AttributeName": "endpoint", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield


@pytest.fixture
def rate_limiter_service(
    initialize_rate_limits_table, settings: Settings
) -> RateLimiterService:
    return RateLimiterService(settings=settings)
