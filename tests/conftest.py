import boto3
import pytest
from moto import mock_dynamodb

from app.config import Configuration
from app.services.cache import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def config() -> Configuration:
    return Configuration()


@pytest.fixture
def dynamodb_client():
    with mock_dynamodb():
        yield boto3.resource('dynamodb')
