import uuid
from random import randint
from typing import List

import boto3
import pendulum
import pytest
from moto import mock_dynamodb

from app.models.post import Post
from app.settings import Settings

CACHE_SERVICE_BASE_URL = 'https://localhost'
JWT_SECRET = '6fl3AkTFmG2rVveLglUW8DOmp8J4Bvi3'


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('DEBUG', 'true')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('STAGE', 'test')

    monkeypatch.setenv('APP_NAME', 'personal-backend-service')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')

    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', CACHE_SERVICE_BASE_URL)
    monkeypatch.setenv('JWT_SECRET', JWT_SECRET)

    monkeypatch.setenv('AWS_REGION', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')

    monkeypatch.setenv('POWERTOOLS_LOGGER_LOG_EVENT', 'true')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'personal')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'personal-backend-service')
    monkeypatch.setenv('POWERTOOLS_TRACE_DISABLED', 'true')


def pytest_configure():
    pytest.cache_service_base_url = CACHE_SERVICE_BASE_URL
    pytest.jwt_secret = JWT_SECRET


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_dynamodb():
        yield boto3.Session().resource(
            'dynamodb',
            region_name='eu-central-1',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_posts_table(dynamodb_resource, posts: List[Post], posts_table):
    dynamodb_resource.create_table(
        TableName='test-posts',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10},
    )
    for post in posts:
        posts_table.put_item(Item=post.dict())


@pytest.fixture
def posts(faker) -> List[Post]:
    posts = []
    for _ in range(5):
        posts.append(
            Post(
                id=str(uuid.uuid4()),
                author=faker.name(),
                content=faker.text(),
                created_at=pendulum.now().to_iso8601_string(),
                deleted_at=None,
                published_at=pendulum.now().to_iso8601_string(),
                slug=faker.slug(),
                tags=faker.words(randint(1, 6)),
                title=faker.sentence(),
                updated_at=None,
                meta={
                    'category': faker.word(),
                    'description': faker.sentence(),
                    'language': 'en',
                    'keywords': faker.words(randint(1, 6)),
                    'title': faker.word(),
                },
            )
        )
    return posts


@pytest.fixture
def posts_table(dynamodb_resource):
    return dynamodb_resource.Table('test-posts')
