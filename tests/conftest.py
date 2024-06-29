import uuid
from random import randint

import boto3
import pendulum
import pytest
from moto import mock_aws

from app.models.post import Post
from app.settings import Settings


def pytest_configure():
    pytest.cache_service_base_url = "https://localhost"
    pytest.jwt_secret = "6fl3AkTFmG2rVveLglUW8DOmp8J4Bvi3"


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name="eu-central-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_posts_table(dynamodb_resource, posts: list[Post], posts_table):
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
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
    for post in posts:
        posts_table.put_item(Item=post.model_dump())


@pytest.fixture
def make_post(faker):
    def make() -> Post:
        now = pendulum.now()
        slug = faker.slug()
        return Post(
            id=str(uuid.uuid4()),
            author=faker.name(),
            content=faker.text(),
            post_path=f"{now.year}/{now.month}/{now.day}/{slug}",
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
def posts(make_post) -> list[Post]:
    posts = []
    for _ in range(5):
        posts.append(make_post())
    return posts


@pytest.fixture
def posts_table(dynamodb_resource):
    return dynamodb_resource.Table("test-posts")
