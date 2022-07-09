import os
from unittest import mock
import uuid

import boto3
import pendulum
import pytest
from moto import mock_dynamodb

from app.auth import JWTToken
from app.settings import Settings
from app.services.cache import CacheService


@pytest.fixture(autouse=True, scope='session')
def setup_environment():
    with mock.patch.dict(os.environ, {
        'APP_NAME': 'personal-backend-service',
        'APP_STAGE': 'test',
        'APP_TIMEZONE': 'Europe/Budapest',
        'AWS_REGION_NAME': 'eu-central-1',
        'AWS_ACCESS_KEY_ID': 'aws-access-key-id',
        'AWS_SECRET_ACCESS_KEY': 'aws-secret-access-key',
        'JWT_SECRET': 'p2s5v8y/B?E(H+MbPeShVmYq3t6w9z$C',
        'CACHE_SERVICE_BASE_URL': 'https://localhost',
        'AWS_ARN_DYNAMODB': 'arn:aws:dynamodb:eu-central-1:345693395407:table/dev-posts'
    }):
        print(os.environ)
        yield


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name=settings.aws_region_name,
                             aws_access_key_id=settings.aws_access_key_id,
                             aws_secret_access_key=settings.aws_secret_access_key)


@pytest.fixture
def jwt_token() -> JWTToken:
    now = pendulum.now()
    return JWTToken(
        exp=now.add(
            hours=1).int_timestamp,
        iat=now.int_timestamp,
        iss='https://netcode.hu',
        jti=str(
            uuid.uuid4()),
        sub={
            'id': str(
                uuid.uuid4()),
            'email': 'info@netcode.hu',
            'display_name': 'root',
            'roles': ['root'],
            'created_at': now.to_iso8601_string(),
            'deleted_at': None,
            'updated_at': None})
