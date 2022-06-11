from typing import List, Any

from fastapi import APIRouter, status
from starlette.responses import Response

from app.models.post import Post
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

router = APIRouter()
post_service = PostService()


@router.post('')
async def create_post(data: CreatePost) -> Any:
    post = post_service.create_post(data.dict())
    return Response(status_code=status.HTTP_201_CREATED, headers={'Location': f'/api/v1/posts/{post.id}'})


async def delete_post(uuid: str) -> Any:
    post_service.delete_post(uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get('')
async def get_all_posts() -> List[Post]:
    return post_service.get_all_posts()


@router.get('/{uuid}')
async def get_post_by_uuid(uuid: str) -> Post:
    return post_service.get_post_by_uuid(uuid)


@router.put('/{uuid}')
async def update_post(uuid: str, data: UpdatePost) -> Any:
    post = post_service.update_post_by_uuid(uuid, data.dict())
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={'Location': f'/api/v1/posts/{post.id}'})
