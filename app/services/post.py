import uuid
from typing import List, Optional

from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr
from slugify import slugify

from app.models.post import Post
from app.repository.post import PostRepository

tracer = Tracer()


def create_slug(title: str, post_uuid: uuid.UUID) -> str:
    return f'{slugify(title)}-{post_uuid}'


class PostFilters:
    NOT_DELETED = Attr('deleted_at').eq(None)
    PUBLISHED = Attr('published_at').ne(None)


class PostService:
    DEFAULT_FIELDS = 'id,title,meta,published_at'

    def __init__(self):
        self._logger = Logger()
        self._repository = PostRepository()

    @tracer.capture_method
    async def create_post(self, data: dict) -> Post:
        data['slug'] = create_slug(data['title'], uuid.uuid4())
        return await self._repository.create_post(data)

    @tracer.capture_method
    async def delete_post(self, post_uuid: str):
        await self._repository.delete_post(post_uuid, PostFilters.NOT_DELETED)
        self._logger.info(f'Post successfully deleted {post_uuid=}')

    @tracer.capture_method
    async def get_all_posts(self, fields: Optional[str] = DEFAULT_FIELDS) -> List[Post]:
        return await self._repository.get_all_posts(
            PostFilters.NOT_DELETED & PostFilters.PUBLISHED, fields
        )

    @tracer.capture_method
    async def get_post(self, post_uuid: str) -> Post:
        return await self._repository.get_post_by_uuid(
            post_uuid, PostFilters.NOT_DELETED
        )

    @tracer.capture_method
    async def update_post(self, post_uuid: str, data: dict):
        await self._repository.update_post(post_uuid, data, PostFilters.NOT_DELETED)
