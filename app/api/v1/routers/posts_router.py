from typing import Annotated

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response

from app.dependencies import get_jwt_bearer, get_post_service
from app.models.auth import JWTToken
from app.models.response import (
    ErrorResponse,
    Page,
    Post as PostResponse,
    ValidationErrorResponse,
)
from app.schemas.post_schema import CreatePost, UpdatePost
from app.services.post_service import PostService

MIN_YEAR = 1970
MAX_YEAR = 2100
MIN_MONTH = 1
MAX_MONTH = 12
MIN_DAY = 1
MAX_DAY = 31

logger = Logger()

router = APIRouter()

# Shared OpenAPI response definitions. Error handlers wrap every failure in
# the ErrorResponse envelope (ValidationErrorResponse for 422).
RESPONSE_400_DATE = {
    400: {"model": ErrorResponse, "description": "Date in the path is out of range"}
}
RESPONSE_403 = {403: {"model": ErrorResponse, "description": "Missing or invalid JWT"}}
RESPONSE_404 = {404: {"model": ErrorResponse, "description": "Post not found"}}
RESPONSE_409 = {
    409: {
        "model": ErrorResponse,
        "description": "A post with this title already exists",
    }
}
RESPONSE_422 = {
    422: {
        "model": ValidationErrorResponse,
        "description": "Request body or path parameters failed validation",
    }
}

POST_UUID = Path(
    description="UUID of the post",
    examples=["84898870-a3f6-45b7-b2af-542728b2d290"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={**RESPONSE_403, **RESPONSE_409, **RESPONSE_422},
    summary="Create a new post",
    description=(
        "The content is stored as Markdown and rendered to HTML when read. "
        "Requires a valid JWT. Returns 409 when a post with the same title "
        "already exists. On success the response body is empty and the new "
        "post is addressed in the `Location` header."
    ),
    response_description="Created — the response body is empty; the new post "
    "is addressed in the Location header",
)
def create_post(
    create_model: CreatePost,
    post_service: Annotated[PostService, Depends(get_post_service)],
    token: Annotated[JWTToken, Depends(get_jwt_bearer)],
) -> Response:
    post = post_service.create_post(create_model.model_dump())
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/posts/{post.id}"},
    )


@router.delete(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**RESPONSE_403, **RESPONSE_404, **RESPONSE_422},
    summary="Soft-delete a post",
    description=(
        "Sets `deletedAt` on the item, so the post is excluded from every "
        "read path while the item is kept in the table. Requires a valid JWT."
    ),
    response_description="Deleted — no content",
)
def delete_post(
    uuid: Annotated[str, POST_UUID],
    post_service: Annotated[PostService, Depends(get_post_service)],
    token: Annotated[JWTToken, Depends(get_jwt_bearer)],
):
    post_service.delete_post(uuid)


@router.get(
    "/archive",
    status_code=status.HTTP_200_OK,
    summary="Get the archive of published posts",
    description=(
        "Maps each year-month to the number of posts published in it, "
        'e.g. `{"2024-02": 3, "2026-08": 1}`.'
    ),
)
def get_archive(
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> dict[str, int]:
    return post_service.get_archive()


@router.get(
    "/{year}/{month}/{day}/{slug}",
    status_code=status.HTTP_200_OK,
    responses={**RESPONSE_400_DATE, **RESPONSE_404, **RESPONSE_422},
    summary="Get a published post by its date path and slug",
    description=(
        "Resolves the post published on the given date with the given URL "
        "slug, e.g. `/api/v1/posts/2026/09/05/notes-on-the-analytical-engine`."
    ),
)
def get_by_post_path(
    slug: Annotated[
        str,
        Path(
            description="URL slug of the post",
            examples=["notes-on-the-analytical-engine"],
        ),
    ],
    post_service: Annotated[PostService, Depends(get_post_service)],
    year: str = Annotated[
        str,
        Path(
            pattern=r"^\d{4}$",
            description="4 digit year",
            examples=["2026"],
        ),
    ],
    month: str = Annotated[
        str,
        Path(
            pattern=r"^(0[1-9]|1[0-2])$",
            description="2 digit month (01-12)",
            examples=["09"],
        ),
    ],
    day: str = Annotated[
        str,
        Path(
            pattern=r"^(0[1-9]|[12]\d|3[01])$",
            description="2 digit day (01-31)",
            examples=["05"],
        ),
    ],
) -> PostResponse:
    year_int = int(year)
    month_int = int(month)
    day_int = int(day)

    if not (
        MIN_YEAR <= year_int <= MAX_YEAR
        and MIN_MONTH <= month_int <= MAX_MONTH
        and MIN_DAY <= day_int <= MAX_DAY
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date"
        )

    return post_service.get_by_post_path(f"{year}/{month}/{day}/{slug}")


@router.get(
    "/{uuid}",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    responses={**RESPONSE_404, **RESPONSE_422},
    summary="Get a single post by UUID",
    description="Returns one post. Soft-deleted posts are not returned.",
)
def get_post_by_uuid(
    uuid: Annotated[str, POST_UUID],
    post_service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    return post_service.get_post(uuid)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    responses=RESPONSE_422,
    summary="List published posts",
    description=(
        "Public endpoint. Results are paginated; pass the returned "
        "`exclusiveStartKey` to fetch the next page, a page without one is "
        "the last. Soft-deleted posts are never returned."
    ),
)
def get_posts(
    post_service: Annotated[PostService, Depends(get_post_service)],
    exclusive_start_key: Annotated[
        str | None,
        Query(
            description="Opaque pagination cursor; pass the `exclusiveStartKey` "
            "from the previous page to fetch the next one"
        ),
    ] = None,
) -> Page:
    return post_service.get_posts(exclusive_start_key)


@router.put(
    "/{uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**RESPONSE_403, **RESPONSE_404, **RESPONSE_422},
    summary="Update an existing post",
    description=(
        "Partial update: only the fields present in the body are replaced, "
        "all fields are optional. Requires a valid JWT."
    ),
    response_description="Updated — no content",
)
def update_post(
    update_model: UpdatePost,
    uuid: Annotated[str, POST_UUID],
    post_service: Annotated[PostService, Depends(get_post_service)],
    token: Annotated[JWTToken, Depends(get_jwt_bearer)],
):
    post_service.update_post(uuid, update_model.model_dump(exclude_none=True))
