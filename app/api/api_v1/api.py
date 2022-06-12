from fastapi import APIRouter
from app.api.api_v1.endpoints import posts

router = APIRouter()
router.include_router(posts.router, prefix='/posts', tags=['posts'])
