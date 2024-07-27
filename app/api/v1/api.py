from fastapi import APIRouter

from app.api.v1.routers import attachments_router, posts_router

posts_router.router.include_router(
    attachments_router.router, prefix="/{post_uuid}/attachments", tags=["attachments"]
)

router = APIRouter(prefix="/api/v1")
router.include_router(posts_router.router, prefix="/posts", tags=["posts"])
