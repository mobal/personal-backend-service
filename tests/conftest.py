import boto3
import pytest
from moto import mock_dynamodb

from app.settings import Settings


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_NAME', 'personal-backend-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')
    monkeypatch.setenv('AWS_REGION_NAME', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')
    monkeypatch.setenv('JWT_SECRET', 'p2s5v8y/B?E(H+MbPeShVmYq3t6w9z$C')
    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', 'https://localhost')
    monkeypatch.setenv(
        'AWS_ARN_DYNAMODB',
        'arn:aws:dynamodb:eu-central-1:345693395407:table/dev-posts')


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='eu-central-1',
                             aws_access_key_id=settings.aws_access_key_id,
                             aws_secret_access_key=settings.aws_secret_access_key)
