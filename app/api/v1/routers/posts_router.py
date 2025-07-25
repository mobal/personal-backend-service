from typing import Any

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import Response

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken
from app.models.response import Page
from app.models.response import Post as PostResponse
from app.schemas.post_schema import CreatePost, UpdatePost
from app.services.post_service import PostService

logger = Logger(utc=True)

jwt_bearer = JWTBearer()
post_service = PostService()
router = APIRouter()


@router.post("")
def create_post(
    create_model: CreatePost, token: JWTToken = Depends(jwt_bearer)
) -> Response:
    post = post_service.create_post(create_model.model_dump())
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/posts/{post.id}"},
    )


@router.delete(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(uuid: str, token: JWTToken = Depends(jwt_bearer)):
    post_service.delete_post(uuid)


@router.get("/archive", status_code=status.HTTP_200_OK)
def get_archive() -> dict[str, Any]:
    return post_service.get_archive()


@router.get("/{year}/{month}/{day}/{slug}", status_code=status.HTTP_200_OK)
def get_by_post_path(
    slug: str,
    year: str = Path(regex=r"^\d{4}$", description="4 digit year"),
    month: str = Path(regex=r"^(0[1-9]|1[0-2])$", description="2 digit month (01-12)"),
    day: str = Path(
        regex=r"^(0[1-9]|[12]\d|3[01])$", description="2 digit day (01-31)"
    ),
) -> PostResponse:
    year_int = int(year)
    month_int = int(month)
    day_int = int(day)

    if not (1970 <= year_int and 1 <= month_int <= 12 and 1 <= day_int <= 31):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date"
        )

    return post_service.get_by_post_path(f"{year}/{month}/{day}/{slug}")


@router.get(
    "/{uuid}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
def get_post_by_uuid(uuid: str) -> PostResponse:
    return post_service.get_post(uuid)


@router.get(
    "",
    response_model=Page,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
)
def get_posts(exclusive_start_key: str | None = None) -> Page:
    return post_service.get_posts(exclusive_start_key)


@router.put(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def update_post(
    update_model: UpdatePost, uuid: str, token: JWTToken = Depends(jwt_bearer)
):
    post_service.update_post(uuid, update_model.model_dump(exclude_none=True))
