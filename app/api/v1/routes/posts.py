from typing import Any, List

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from starlette.responses import Response

from app.auth import JWTBearer
from app.models.auth import JWTToken, User
from app.models.response import Post as PostResponse
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

logger = Logger()

jwt_bearer = JWTBearer()
metrics = Metrics()
post_service = PostService()
router = APIRouter()
tracer = Tracer()


@tracer.capture_method
async def authorize(required_privileges: List[str], token: JWTToken) -> bool:
    user = User(**token.sub)
    if set(required_privileges).issubset(user.roles) or 'root' in user.roles:
        return True
    raise await create_http_exception(
        status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized'
    )


@tracer.capture_method
async def create_http_exception(
    status_code: int = status.HTTP_403_FORBIDDEN, detail: str = 'Not authenticated'
):
    raise HTTPException(status_code=status_code, detail=detail)


@router.post('')
@tracer.capture_method
async def create_post(
    request: Request, token: JWTToken = Depends(jwt_bearer)
) -> Response:
    if await authorize(['post:create'], token):
        model = CreatePost.parse_raw(await request.body())
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
@tracer.capture_method
async def delete_post(uuid: str, token: JWTToken = Depends(jwt_bearer)):
    if await authorize(['post:delete'], token):
        await post_service.delete_post(uuid)
        metrics.add_metric(name='DeletePost', unit=MetricUnit.Count, value=1)


@router.get(
    '',
    response_model=List[PostResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
@tracer.capture_method
async def get_all_posts() -> List[PostResponse]:
    posts = await post_service.get_all_posts()
    metrics.add_metric(name='GetAllPosts', unit=MetricUnit.Count, value=1)
    return posts


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


@router.put(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
)
@tracer.capture_method
async def update_post(
    request: Request, uuid: str, token: JWTToken = Depends(jwt_bearer)
):
    if await authorize(['post:edit'], token):
        model = UpdatePost.parse_raw(await request.body())
        await post_service.update_post(uuid, model)
        metrics.add_metric(name='UpdatePost', unit=MetricUnit.Count, value=1)
