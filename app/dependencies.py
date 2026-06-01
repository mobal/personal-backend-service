from functools import lru_cache
from typing import Annotated

import boto3
from fastapi import Depends, Request

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken
from app.repositories.post_repository import PostRepository
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.publisher_service import PublisherService
from app.services.rate_limiter_service import RateLimiterService
from app.services.s3_storage_service import S3StorageService
from app.services.sshfs_storage_service import SSHFSStorageService
from app.settings import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_db_client() -> boto3.resource:
    return boto3.resource("dynamodb")


def get_s3_client() -> boto3.client:
    return boto3.client("s3")


def get_post_repository(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[boto3.resource, Depends(get_db_client)],
) -> PostRepository:
    return PostRepository(
        settings=settings,
        table_name=f"{settings.stage}-posts",
        db_resource=db,
    )


def get_post_service(
    repo: Annotated[PostRepository, Depends(get_post_repository)],
) -> PostService:
    return PostService(repo=repo)


def get_s3_storage_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> S3StorageService:
    return S3StorageService(
        settings=settings,
        region=settings.aws_region,
    )


def get_sshfs_storage_service() -> SSHFSStorageService:
    return SSHFSStorageService()


def get_attachment_service(
    post_service: Annotated[PostService, Depends(get_post_service)],
    s3_service: Annotated[S3StorageService, Depends(get_s3_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AttachmentService:
    return AttachmentService(
        settings=settings,
        post_service=post_service,
        storage_service=s3_service,
    )


def get_publisher_service(
    post_service: Annotated[PostService, Depends(get_post_service)],
    sshfs_service: Annotated[SSHFSStorageService, Depends(get_sshfs_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PublisherService:
    return PublisherService(
        post_service=post_service,
        storage_service=sshfs_service,
        settings=settings,
    )


def get_rate_limiter_service(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[boto3.resource, Depends(get_db_client)],
) -> RateLimiterService:
    return RateLimiterService(
        settings=settings,
        stage=settings.stage,
        max_requests=settings.rate_limit_requests,
        window_duration=settings.rate_limit_duration_in_seconds,
        db_resource=db,
    )


def get_jwt_bearer(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTToken:
    """FastAPI dependency that validates JWT and returns the decoded token."""
    bearer = JWTBearer(jwt_secret=settings.jwt_secret)
    token = bearer(request)
    # JWTBearer with auto_error=True (default) always returns JWTToken or raises
    assert token is not None
    return token
