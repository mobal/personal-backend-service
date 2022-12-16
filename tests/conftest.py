import uuid
from typing import Any

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
    monkeypatch.setenv('APP_DEBUG', 'true')
    monkeypatch.setenv('APP_NAME', 'personal-backend-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')

    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', CACHE_SERVICE_BASE_URL)
    monkeypatch.setenv('JWT_SECRET', JWT_SECRET)

    monkeypatch.setenv('AWS_REGION', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')

    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('POWERTOOLS_LOGGER_LOG_EVENT', 'true')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'personal')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'personal-backend-service')


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
def initialize_posts_table(dynamodb_resource, post_model: Post, posts_table):
    dynamodb_resource.create_table(
        TableName='test-posts',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10},
    )
    posts_table.put_item(Item=post_model.dict())


@pytest.fixture
def post_dict() -> dict[str, Any]:
    now = pendulum.now()
    tags = ['list', 'of', 'keywords']
    title = 'Some random title'
    return {
        'author': 'root',
        'title': title,
        'content': 'Some random content',
        'created_at': now.to_iso8601_string(),
        'published_at': now.to_iso8601_string(),
        'tags': tags,
        'meta': {
            'category': 'random',
            'description': 'Meta description',
            'language': 'en',
            'keywords': tags,
            'title': title,
        },
    }


@pytest.fixture
def post_model(post_dict: dict) -> Post:
    return Post.parse_obj(
        {
            'id': str(uuid.uuid4()),
            'author': post_dict['author'],
            'content': post_dict['content'],
            'created_at': post_dict['created_at'],
            'deleted_at': None,
            'published_at': post_dict['published_at'],
            'slug': 'some-random-title',
            'tags': post_dict['tags'],
            'title': post_dict['title'],
            'updated_at': None,
            'meta': post_dict['meta'],
        }
    )


@pytest.fixture
def posts_table(dynamodb_resource):
    return dynamodb_resource.Table('test-posts')
