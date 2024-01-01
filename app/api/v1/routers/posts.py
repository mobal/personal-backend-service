import functools
from typing import Any, List

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from fastapi import APIRouter, Depends, HTTPException, Path, status
from starlette.responses import Response

from app.auth import JWTBearer
from app.models.auth import JWTToken, Role, User
from app.models.response import Page
from app.models.response import Post as PostResponse
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

logger = Logger(utc=True)

jwt_bearer = JWTBearer()
metrics = Metrics()
post_service = PostService()
router = APIRouter()
tracer = Tracer()


@tracer.capture_method
def authorize(roles: List[str]):
    def decorator_wrapper(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            user = User(**kwargs['token'].sub)
            if all(role in user.roles for role in roles):
                return await func(*args, **kwargs)
            else:
                logger.warning(f'The {user=} does not have the appropriate {roles=}')
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized'
                )

        return wrapper

    return decorator_wrapper


@router.post('')
@authorize(roles=[Role.POST_CREATE])
@tracer.capture_method
async def create_post(
    model: CreatePost, token: JWTToken = Depends(jwt_bearer)
) -> Response:
    post = await post_service.create_post(model)
    metrics.add_metric(name='CreatePost', unit=MetricUnit.Count, value=1)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={'Location': f'/api/v1/posts/{post.id}'},
    )


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
)
@authorize(roles=[Role.POST_DELETE])
@tracer.capture_method
async def delete_post(uuid: str, token: JWTToken = Depends(jwt_bearer)):
    await post_service.delete_post(uuid)
    metrics.add_metric(name='DeletePost', unit=MetricUnit.Count, value=1)


@router.get('/archive', status_code=status.HTTP_200_OK)
@tracer.capture_method
async def get_archive() -> dict[str, Any]:
    archive = await post_service.get_archive()
    metrics.add_metric(name='GetArchive', unit=MetricUnit.Count, value=1)
    return archive


@router.get('/{year}/{month}/{day}/{slug}', status_code=status.HTTP_200_OK)
@tracer.capture_method
async def get_post_by_date_and_slug(
    slug: str,
    year: int = Path(ge=1970),
    month: int = Path(ge=1, le=12),
    day: int = Path(ge=1, le=31),
) -> PostResponse:
    post_response = await post_service.get_post_by_date_and_slug(year, month, day, slug)
    metrics.add_metric(name='GetPostByDateAndSlug', unit=MetricUnit.Count, value=1)
    return post_response


@router.get('/{uuid}', status_code=status.HTTP_200_OK)
@tracer.capture_method
async def get_post_by_uuid(uuid: str) -> PostResponse:
    post_response = await post_service.get_post(uuid)
    metrics.add_metric(name='GetPostByUuid', unit=MetricUnit.Count, value=1)
    return post_response


@router.get(
    '',
    response_model=Page,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
@tracer.capture_method
async def get_posts(exclusive_start_key: (str | None) = None) -> Page:
    if exclusive_start_key:
        response = await post_service.get_posts(exclusive_start_key)
    else:
        response = await post_service.get_posts()
    metrics.add_metric(name='GetPosts', unit=MetricUnit.Count, value=1)
    return response


@router.put(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
)
@authorize(roles=[Role.POST_UPDATE])
@tracer.capture_method
async def update_post(
    model: UpdatePost, uuid: str, token: JWTToken = Depends(jwt_bearer)
):
    await post_service.update_post(uuid, model)
    metrics.add_metric(name='UpdatePost', unit=MetricUnit.Count, value=1)