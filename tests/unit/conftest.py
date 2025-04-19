import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, ConditionBase

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken, Role
from app.repositories.post_repository import PostRepository
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.storage_service import StorageService


@pytest.fixture
def attachment_service() -> AttachmentService:
    return AttachmentService()


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def filter_expression() -> ConditionBase:
    return Attr("deleted_at").eq(None) & Attr("published_at").ne(None)


@pytest.fixture
def jwt_token() -> JWTToken:
    now = pendulum.now()
    return JWTToken(
        exp=now.add(years=1).int_timestamp,
        iat=now.int_timestamp,
        iss="https://netcode.hu",
        jti=str(uuid.uuid4()),
        sub={
            "id": str(uuid.uuid4()),
            "email": "info@netcode.hu",
            "display_name": "root",
            "roles": [Role.POST_CREATE, Role.POST_DELETE, Role.POST_UPDATE],
            "created_at": now.to_iso8601_string(),
            "deleted_at": None,
            "updated_at": None,
        },
    )


@pytest.fixture
def jwt_token_without_roles(jwt_token: JWTToken) -> JWTToken:
    jwt_token.sub["roles"] = []
    return jwt_token


@pytest.fixture
def post_repository(initialize_posts_table) -> PostRepository:
    return PostRepository()


@pytest.fixture
def post_service() -> PostService:
    return PostService()


@pytest.fixture
def storage_service() -> StorageService:
    return StorageService()
