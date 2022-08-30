import uuid
from typing import List, Optional

import markdown
import pendulum
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr
from slugify import slugify

from app.models.post import Post
from app.models.response import Post as PostResponse
from app.repositories.post import PostRepository
from app.schemas.post import CreatePost, UpdatePost

tracer = Tracer()


class PostFilters:
    NOT_DELETED = Attr('deleted_at').eq(None) | Attr('deleted_at').not_exists()
    PUBLISHED = Attr('published_at').ne(None)


class PostService:
    DEFAULT_FIELDS = 'id,title,meta,published_at'

    def __init__(self):
        self._logger = Logger()
        self._repository = PostRepository()

    @tracer.capture_method
    async def create_post(self, create_post: CreatePost) -> Post:
        post_uuid = uuid.uuid4()
        data = create_post.dict()
        data['id'] = str(post_uuid)
        data['created_at'] = pendulum.now().to_iso8601_string()
        data['deleted_at'] = None
        data['slug'] = slugify(data["title"])
        data['updated_at'] = None
        await self._repository.create_post(data)
        return Post(**data)

    @tracer.capture_method
    async def delete_post(self, post_uuid: str):
        item = await self._repository.get_post_by_uuid(
            post_uuid, PostFilters.NOT_DELETED
        )
        item['deleted_at'] = pendulum.now().to_iso8601_string()
        await self._repository.update_post(post_uuid, item, PostFilters.NOT_DELETED)
        self._logger.info(f'Post successfully deleted {post_uuid=}')

    @tracer.capture_method
    async def get_all_posts(
        self, fields: Optional[str] = DEFAULT_FIELDS
    ) -> List[PostResponse]:
        items = await self._repository.get_all_posts(
            PostFilters.NOT_DELETED & PostFilters.PUBLISHED, fields
        )
        result = []
        for item in items:
            result.append(PostResponse(**item))
        return result

    @tracer.capture_method
    async def get_post(self, post_uuid: str) -> PostResponse:
        item = await self._repository.get_post_by_uuid(
            post_uuid, PostFilters.NOT_DELETED
        )
        if item.get('content'):
            item['content'] = markdown.markdown(item['content'])
        return PostResponse(**item)

    @tracer.capture_method
    async def update_post(self, post_uuid: str, update_post: UpdatePost):
        data = update_post.dict(exclude_unset=True)
        data['updated_at'] = pendulum.now().to_iso8601_string()
        if update_post.title:
            data['slug'] = slugify(update_post.title)
        await self._repository.update_post(post_uuid, data, PostFilters.NOT_DELETED)
        self._logger.info(f'Post successfully updated {post_uuid=}')

    @tracer.capture_method
    async def get_archive(self) -> dict[str, int]:
        items = await self._repository.get_all_posts(
            PostFilters.NOT_DELETED & PostFilters.PUBLISHED, 'id,published_at'
        )
        archive = {}
        if items:
            dates = list(map(lambda x: x['published_at'], items))
            for dt in pendulum.period(
                pendulum.parse(min(dates)).start_of('month'),
                pendulum.parse(max(dates)).end_of('month'),
            ).range('months'):
                result = list(
                    filter(
                        lambda x, start=dt, end=dt.end_of('month'): start
                        <= pendulum.parse(x)
                        <= end,
                        dates,
                    )
                )
                archive[dt.format('YYYY-MM')] = len(result)
        return archive
