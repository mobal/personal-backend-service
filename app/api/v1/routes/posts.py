from typing import List

from aws_lambda_powertools.metrics import Metrics, MetricUnit
from fastapi import status, APIRouter, Depends, Request, HTTPException
from starlette.responses import Response

from app.auth import JWTBearer
from app.models.auth import JWTToken, User
from app.models.post import Post
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

jwt_bearer = JWTBearer(auto_error=True)
metrics = Metrics()
post_service = PostService()
router = APIRouter()


async def authorize(required_privileges: List[str], token: JWTToken) -> bool:
    if token:
        user = User.parse_obj(token.sub)
        if set(required_privileges).issubset(user.roles):
            return True
        raise await create_http_exception(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authorized'
        )
    raise create_http_exception()


async def create_http_exception(
    status_code: int = status.HTTP_403_FORBIDDEN, detail: str = 'Not authenticated'
):
    raise HTTPException(status_code=status_code, detail=detail)


@router.post('')
async def create_post(
    request: Request, token: JWTToken = Depends(jwt_bearer)
) -> Response:
    if await authorize(['post:create'], token):
        model = CreatePost.parse_raw(await request.body())
        post = await post_service.create_post(model.dict())
        metrics.add_metric(name='CreatePost', unit=MetricUnit.Count, value=1)
        return Response(
            status_code=status.HTTP_201_CREATED,
            headers={'Location': f'/api/v1/posts/{post.id}'},
        )


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post(uuid: str, token: JWTToken = Depends(jwt_bearer)):
    if await authorize(['post:delete'], token):
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
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_post(
    request: Request, uuid: str, token: JWTToken = Depends(jwt_bearer)
):
    if await authorize(['post:edit'], token):
        model = UpdatePost.parse_raw(await request.body())
        await post_service.update_post(uuid, model.dict())
        metrics.add_metric(name='UpdatePost', unit=MetricUnit.Count, value=1)
