from fastapi import APIRouter

from app.api.v1.routers import posts

router = APIRouter(prefix="/api/v1")
router.include_router(posts.router, prefix="/posts", tags=["posts"])
