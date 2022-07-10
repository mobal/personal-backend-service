from app.services.cache import CacheService
from app.services.post import PostService


def cache_service() -> CacheService:
    return CacheService()


def post_service() -> PostService:
    return PostService()
