from typing import List

from fastapi import APIRouter, status, Depends, HTTPException
from starlette.responses import Response

from app.auth import JWTAuth
from app.models.post import Post
from app.schemas.post import CreatePost, UpdatePost
from app.services.post import PostService

jwt_auth = JWTAuth()
post_service = PostService()
router = APIRouter()


@router.post('', dependencies=[Depends(jwt_auth)])
async def create_post(data: CreatePost) -> Response:
    post = await post_service.create_post(data.dict())
    return Response(status_code=status.HTTP_201_CREATED, headers={'Location': f'/api/v1/posts/{post.id}'})


@router.delete('/{uuid}', dependencies=[Depends(jwt_auth)], status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(uuid: str):
    await post_service.delete_post(uuid)


@router.get('', status_code=status.HTTP_200_OK)
async def get_all_posts() -> List[Post]:
    return await post_service.get_all_posts()


@router.get('/{uuid}', status_code=status.HTTP_200_OK)
async def get_post_by_uuid(uuid: str) -> Post:
    post = await post_service.get_post(uuid)
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f'The requested post was not found with id {uuid}')
    return post


@router.put('/{uuid}', dependencies=[Depends(jwt_auth)], status_code=status.HTTP_204_NO_CONTENT)
async def update_post(uuid: str, data: UpdatePost):
    await post_service.update_post(uuid, data.dict())
