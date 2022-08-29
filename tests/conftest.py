import boto3
import pytest
from moto import mock_dynamodb

from app.settings import Settings


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_DEBUG', 'true')
    monkeypatch.setenv('APP_NAME', 'personal-backend-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')

    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', 'https://localhost')
    monkeypatch.setenv('JWT_SECRET', '6fl3AkTFmG2rVveLglUW8DOmp8J4Bvi3')

    monkeypatch.setenv('AWS_REGION_NAME', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')

    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    monkeypatch.setenv('POWERTOOLS_LOGGER_LOG_EVENT', 'true')
    monkeypatch.setenv('POWERTOOLS_METRICS_NAMESPACE', 'personal')
    monkeypatch.setenv('POWERTOOLS_SERVICE_NAME', 'personal-backend-service')


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_dynamodb():
        yield boto3.resource(
            'dynamodb',
            region_name='eu-central-1',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
