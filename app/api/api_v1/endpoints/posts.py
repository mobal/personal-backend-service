from typing import List, Any

from fastapi import APIRouter, status, Depends
from starlette.responses import Response

from app.auth import JWTAuth, JWTToken
from app.models.post import Post
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

router = APIRouter()
post_service = PostService()


@router.post('')
async def create_post(data: CreatePost, token: JWTToken = Depends(JWTAuth())) -> Any:
    post = post_service.create_post(data.dict())
    return Response(status_code=status.HTTP_201_CREATED, headers={'Location': f'/api/v1/posts/{post.id}'})


@router.delete('/{uuid}', dependencies=[Depends(JWTAuth())])
async def delete_post(uuid: str) -> Any:
    post_service.delete_post(uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('')
async def get_all_posts() -> List[Post]:
    return post_service.get_all_posts()


@router.get('/{uuid}')
async def get_post_by_uuid(uuid: str) -> Post:
    return post_service.get_post(uuid)


@router.put('/{uuid}', dependencies=[Depends(JWTAuth())])
async def update_post(uuid: str, data: UpdatePost) -> Any:
    post_service.update_post(uuid, data.dict())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
