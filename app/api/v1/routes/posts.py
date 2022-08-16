from typing import List

from aws_lambda_powertools.metrics import MetricUnit
from fastapi import APIRouter, status, Depends
from starlette.responses import Response

from app.auth import JWTBearer
from app.models.post import Post
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService
from app.utils import metrics

jwt_bearer = JWTBearer()
post_service = PostService()
router = APIRouter()


@router.post('', dependencies=[Depends(jwt_bearer)])
async def create_post(body: CreatePost) -> Response:
    post = await post_service.create_post(body.dict())
    metrics.add_metric(name='CreatePost', unit=MetricUnit.Count, value=1)
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={'Location': f'/api/v1/posts/{post.id}'},
    )


@router.delete(
    '/{uuid}',
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post(uuid: str):
    await post_service.delete_post(uuid)
    metrics.add_metric(name='DeletePost', unit=MetricUnit.Count, value=1)


@router.get('', status_code=status.HTTP_200_OK)
async def get_all_posts() -> List[Post]:
    posts = await post_service.get_all_posts()
    metrics.add_metric(name='GetAllPosts', unit=MetricUnit.Count, value=1)
    return posts


@router.get('/{uuid}', status_code=status.HTTP_200_OK)
async def get_post_by_uuid(uuid: str) -> Post:
    post = await post_service.get_post(uuid)
    metrics.add_metric(name='GetPostByUuid', unit=MetricUnit.Count, value=1)
    return post


@router.put(
    '/{uuid}',
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_post(uuid: str, data: UpdatePost):
    await post_service.update_post(uuid, data.dict())
    metrics.add_metric(name='UpdatePost', unit=MetricUnit.Count, value=1)
