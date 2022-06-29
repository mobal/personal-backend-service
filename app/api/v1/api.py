from fastapi import APIRouter

from app.api.v1.routes import posts

router = APIRouter()
router.include_router(posts.router, prefix='/posts', tags=['posts'])
