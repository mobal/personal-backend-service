import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, AttributeBase

from app.auth import JWTBearer
from app.models.auth import JWTToken
from app.models.post import Post
from app.repositories.post import PostRepository
from app.services.cache import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def post_fields() -> str:
    return ','.join(Post.__fields__)


@pytest.fixture
def filter_expression() -> AttributeBase:
    return Attr('deleted_at').eq(None) & Attr('published_at').ne(None)


@pytest.fixture
def jwt_token() -> JWTToken:
    now = pendulum.now()
    return JWTToken(
        exp=now.add(hours=1).int_timestamp,
        iat=now.int_timestamp,
        iss='https://netcode.hu',
        jti=str(uuid.uuid4()),
        sub={
            'id': str(uuid.uuid4()),
            'email': 'info@netcode.hu',
            'display_name': 'root',
            'roles': ['post:create', 'post:delete', 'post:edit'],
            'created_at': now.to_iso8601_string(),
            'deleted_at': None,
            'updated_at': None,
        },
    )


@pytest.fixture
def jwt_token_without_roles(jwt_token: JWTToken) -> JWTToken:
    jwt_token.sub['roles'] = []
    return jwt_token


@pytest.fixture
def post_repository(initialize_posts_table) -> PostRepository:
    return PostRepository()
