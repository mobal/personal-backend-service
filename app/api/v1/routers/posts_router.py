from typing import Any

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Path, status
from starlette.responses import Response

from app.api.decorators import authorize
from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken, Role
from app.models.response import Page
from app.models.response import Post as PostResponse
from app.schemas.post_schema import CreatePost, UpdatePost
from app.services.post_service import PostService

logger = Logger(utc=True)

jwt_bearer = JWTBearer()
post_service = PostService()
router = APIRouter()


@router.post("")
@authorize(roles=[Role.POST_CREATE])
async def create_post(
    create_model: CreatePost, token: JWTToken = Depends(jwt_bearer)
) -> Response:
    post = await post_service.create_post(create_model.model_dump())
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/posts/{post.id}"},
    )


@router.delete(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@authorize(roles=[Role.POST_DELETE])
async def delete_post(uuid: str, token: JWTToken = Depends(jwt_bearer)):
    await post_service.delete_post(uuid)


@router.get("/archive", status_code=status.HTTP_200_OK)
async def get_archive() -> dict[str, Any]:
    return await post_service.get_archive()


@router.get("/{year}/{month}/{day}/{slug}", status_code=status.HTTP_200_OK)
async def get_by_post_path(
    slug: str,
    year: int = Path(ge=1970),
    month: int = Path(ge=1, le=12),
    day: int = Path(ge=1, le=31),
) -> PostResponse:
    return await post_service.get_by_post_path(f"{year}/{month}/{day}/{slug}")


@router.get(
    "/{uuid}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def get_post_by_uuid(uuid: str) -> PostResponse:
    return await post_service.get_post(uuid)


@router.get(
    "",
    response_model=Page,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
async def get_posts(exclusive_start_key: str | None = None) -> Page:
    return await post_service.get_posts(exclusive_start_key)


@router.put(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@authorize(roles=[Role.POST_UPDATE])
async def update_post(
    update_model: UpdatePost, uuid: str, token: JWTToken = Depends(jwt_bearer)
):
    await post_service.update_post(uuid, update_model.model_dump(exclude_none=True))
