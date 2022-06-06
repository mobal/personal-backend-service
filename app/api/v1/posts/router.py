from fastapi import APIRouter

from app.api.v1.posts.service import PostService

router = APIRouter()
post_service = PostService()


@router.get('')
async def posts():
    return post_service.get_all_posts()


@router.get('/{uuid}')
async def post(uuid: str):
    return post_service.get_post_by_id(uuid)
