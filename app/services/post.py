import uuid
from typing import List

from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr
from slugify import slugify

from app.models.post import Post
from app.repository.post import PostRepository

tracer = Tracer()


def create_slug(title: str, post_uuid: uuid.UUID) -> str:
    return f'{slugify(title)}-{post_uuid}'


class PostService:
    NOT_DELETED_FILTER = Attr('deleted_at').eq(None)

    def __init__(self):
        self._logger = Logger()
        self._repository = PostRepository()

    @tracer.capture_method
    async def create_post(self, data: dict) -> Post:
        data['slug'] = create_slug(data['title'], uuid.uuid4())
        return await self._repository.create_post(data)

    @tracer.capture_method
    async def delete_post(self, post_uuid: str):
        await self._repository.delete_post(post_uuid, self.NOT_DELETED_FILTER)
        self._logger.info(f'Post successfully deleted {post_uuid=}')

    @tracer.capture_method
    async def get_all_posts(self) -> List[Post]:
        return await self._repository.get_all_posts(self.NOT_DELETED_FILTER)

    @tracer.capture_method
    async def get_post(self, post_uuid: str) -> Post:
        return await self._repository.get_post_by_uuid(
            post_uuid, self.NOT_DELETED_FILTER
        )

    @tracer.capture_method
    async def update_post(self, post_uuid: str, data: dict):
        await self._repository.update_post(post_uuid, data, self.NOT_DELETED_FILTER)
