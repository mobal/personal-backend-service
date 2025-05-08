import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, ConditionBase

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken
from app.repositories.post_repository import PostRepository
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService
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
def jwt_token(user_dict: dict[str, str | None]) -> JWTToken:
    now = pendulum.now()
    return JWTToken(
        exp=now.add(years=1).int_timestamp,
        iat=now.int_timestamp,
        iss="https://netcode.hu",
        jti=str(uuid.uuid4()),
        sub=user_dict["id"],
        user=user_dict,
    )


@pytest.fixture
def post_repository(initialize_posts_table) -> PostRepository:
    return PostRepository()


@pytest.fixture
def post_service() -> PostService:
    return PostService()


@pytest.fixture
def publisher_service() -> PublisherService:
    return PublisherService()


@pytest.fixture
def storage_service() -> StorageService:
    return StorageService()
