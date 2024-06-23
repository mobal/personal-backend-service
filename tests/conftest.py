import os
import uuid
from random import randint
from typing import List

import boto3
import pendulum
import pytest
from moto import mock_aws

from app.models.post import Post
from app.settings import Settings


def pytest_configure():
    pytest.cache_service_base_url = "https://localhost"
    pytest.jwt_secret = "6fl3AkTFmG2rVveLglUW8DOmp8J4Bvi3"


def pytest_sessionstart():
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["STAGE"] = "test"

    os.environ["APP_NAME"] = "personal-backend-service"
    os.environ["APP_TIMEZONE"] = "Europe/Budapest"

    os.environ["CACHE_SERVICE_BASE_URL"] = pytest.cache_service_base_url
    os.environ["JWT_SECRET"] = pytest.jwt_secret

    os.environ["AWS_REGION"] = "eu-central-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "aws_access_key_id"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "aws_secret_access_key"

    os.environ["POWERTOOLS_LOGGER_LOG_EVENT"] = "true"
    os.environ["POWERTOOLS_SERVICE_NAME"] = "personal-backend-service"


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
def initialize_posts_table(dynamodb_resource, posts: List[Post], posts_table):
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
def posts(make_post) -> List[Post]:
    posts = []
    for _ in range(5):
        posts.append(make_post())
    return posts


@pytest.fixture
def posts_table(dynamodb_resource):
    return dynamodb_resource.Table("test-posts")
