import base64
import uuid
from random import randint

import boto3
import pendulum
import pytest
from moto import mock_aws

from app.models.post import Attachment, Post
from app.settings import Settings


def pytest_configure():
    pytest.aws_default_region = "eu-central-1"
    pytest.jwt_secret_ssm_param_name = "/dev/secrets/secret"
    pytest.jwt_secret_ssm_param_value = "94k9yz00rw"


@pytest.fixture(autouse=True)
def setup():
    with mock_aws():
        ssm_client = boto3.client("ssm")
        ssm_client.put_parameter(
            Name=pytest.jwt_secret_ssm_param_name,
            Value=pytest.jwt_secret_ssm_param_value,
            Type="SecureString",
        )
        yield


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def attachment(test_data: bytes) -> Attachment:
    now = pendulum.now()
    file_name = "lorem.txt"
    return Attachment(
        id=str(uuid.uuid4()),
        bucket="attachments",
        content_length=len(test_data),
        display_name=file_name,
        mime_type="plain/text",
        name=f"/{now.year}/{now.month}/{now.day}/post_with_attachment/{file_name}",
    )


@pytest.fixture
def dynamodb_resource(settings: Settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name="eu-central-1",
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
def make_post(faker):
    def make() -> Post:
        now = pendulum.now()
        slug = faker.slug()
        return Post(
            id=str(uuid.uuid4()),
            author=faker.name(),
            content=faker.text(),
            post_path=f"{now.format("YYYY/MM/DD")}/{slug}",
            created_at=now.to_iso8601_string(),
            deleted_at=None,
            published_at=now.to_iso8601_string(),
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
def s3_resource(settings: Settings):
    with mock_aws():
        yield boto3.Session().resource(
            "s3",
            region_name="eu-central-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def test_data() -> bytes:
    return base64.b64encode(
        "Lorem ipsum odor amet, consectetuer adipiscing elit.".encode("utf-8")
    )


@pytest.fixture
def user_dict() -> dict[str, str | None]:
    return {
        "id": str(uuid.uuid4()),
        "email": "info@netcode.hu",
        "display_name": "root",
        "created_at": pendulum.now().to_iso8601_string(),
        "deleted_at": None,
        "updated_at": None,
    }
