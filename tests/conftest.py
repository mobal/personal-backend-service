import base64
import os
import uuid
from datetime import UTC, datetime
from random import randint

import boto3
import pytest
from moto import mock_aws

from app.models.post import Attachment, Post
from app.settings import Settings


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    with mock_aws():
        monkeypatch.setenv(
            "JWT_SECRET_SSM_PARAM_NAME", os.getenv("JWT_SECRET_SSM_PARAM_NAME")
        )
        ssm_client = boto3.client(
            "ssm",
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        ssm_client.put_parameter(
            Name=os.getenv("JWT_SECRET_SSM_PARAM_NAME"),
            Value=os.getenv("JWT_SECRET_SSM_PARAM_VALUE"),
            Type="SecureString",
        )
        yield


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def attachment(test_data: bytes, aws_default_region: str) -> Attachment:
    now = datetime.now(UTC)
    file_name = "lorem.txt"
    return Attachment(
        id=str(uuid.uuid4()),
        bucket="attachments",
        content_length=len(test_data),
        display_name=file_name,
        mime_type="plain/text",
        name=f"/{now.year}/{now.month}/{now.day}/post_with_attachment/{file_name}",
        region=aws_default_region,
    )


@pytest.fixture
def aws_default_region() -> str:
    return os.getenv("AWS_DEFAULT_REGION")


@pytest.fixture
def dynamodb_resource(aws_default_region: str, settings: Settings):
    yield boto3.Session().resource(
        "dynamodb",
        region_name=aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


@pytest.fixture
def initialize_posts_table(
    dynamodb_resource, posts: list[Post], post_with_attachment: Post, posts_table
):
    dynamodb_resource.create_table(
        AttributeDefinitions=[
            {
                "AttributeName": "id",
                "AttributeType": "S",
            },
            {
                "AttributeName": "post_path",
                "AttributeType": "S",
            },
            {
                "AttributeName": "title",
                "AttributeType": "S",
            },
            {
                "AttributeName": "created_at",
                "AttributeType": "S",
            },
        ],
        TableName="test-posts",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "PostPathIndex",
                "KeySchema": [
                    {
                        "AttributeName": "post_path",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
            {
                "IndexName": "TitleIndex",
                "KeySchema": [
                    {
                        "AttributeName": "title",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
            {
                "IndexName": "CreatedAtIndex",
                "KeySchema": [
                    {
                        "AttributeName": "created_at",
                        "KeyType": "HASH",
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    posts.append(post_with_attachment)
    with posts_table.batch_writer() as batch:
        for post in posts:
            batch.put_item(Item=post.model_dump())


@pytest.fixture
def jwt_secret_ssm_param_value() -> str:
    return os.getenv("JWT_SECRET_SSM_PARAM_VALUE")


@pytest.fixture
def make_post(faker):
    def make() -> Post:
        now = datetime.now(UTC)
        slug = faker.slug()
        return Post(
            id=str(uuid.uuid4()),
            author=faker.name(),
            content=faker.text(),
            post_path=f"{now.strftime('%Y/%m/%d')}/{slug}",
            created_at=now.isoformat(),
            deleted_at=None,
            published_at=now.isoformat(),
            slug=slug,
            tags=faker.words(randint(1, 6)),
            title=faker.sentence(),
            updated_at=None,
            meta={
                "category": faker.word(),
                "description": faker.sentence(),
                "language": "en",
                "keywords": faker.words(randint(1, 6)),
                "title": faker.word(),
            },
        )

    return make


@pytest.fixture
def post_with_attachment(attachment: Attachment, make_post) -> Post:
    post = make_post()
    post.attachments = [attachment]
    return post


@pytest.fixture
def posts(make_post) -> list[Post]:
    posts = []
    for _ in range(10):
        posts.append(make_post())
    return posts


@pytest.fixture
def posts_table(dynamodb_resource):
    return dynamodb_resource.Table("test-posts")


@pytest.fixture
def s3_resource(aws_default_region: str, settings: Settings):
    yield boto3.Session().resource(
        "s3",
        region_name=aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


@pytest.fixture
def test_data() -> bytes:
    return base64.b64encode(b"Lorem ipsum odor amet, consectetuer adipiscing elit.")


@pytest.fixture
def user_dict() -> dict[str, str | None]:
    return {
        "id": str(uuid.uuid4()),
        "email": "info@netcode.hu",
        "display_name": "root",
        "created_at": datetime.now(UTC).isoformat(),
        "deleted_at": None,
        "updated_at": None,
    }
