import uuid
from typing import Optional

import markdown
import pendulum
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from slugify import slugify

from app.exceptions import PostAlreadyExistsException, PostNotFoundException
from app.models.post import Post
from app.models.response import Page
from app.models.response import Post as PostResponse
from app.repositories.post import PostRepository
from app.schemas.post import CreatePost, UpdatePost


class FilterExpressions:
    NOT_DELETED = Attr("deleted_at").eq(None) | Attr("deleted_at").not_exists()
    PUBLISHED = Attr("published_at").ne(None)


async def _item_to_response(item: dict, to_markdown: bool = False) -> PostResponse:
    if item.get("content") and to_markdown:
        item["content"] = markdown.markdown(item["content"])
    return PostResponse(**item)


class PostService:
    ERROR_MESSAGE_POST_ALREADY_EXISTS: str = "There is already a post with this title"
    ERROR_MESSAGE_POST_WAS_NOT_FOUND: str = "The requested post was not found"

    def __init__(self):
        self._logger = Logger(utc=True)
        self._repository = PostRepository()

    async def _get_post_by_uuid(self, post_uuid: str) -> Post:
        item = await self._repository.get_post_by_uuid(
            post_uuid, FilterExpressions.NOT_DELETED
        )
        if item is None:
            self._logger.warning(f"Post was not found with UUID {post_uuid=}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        return Post(**item)

    async def create_post(self, create_post: CreatePost) -> Post:
        now = pendulum.now()
        filter_expression = Attr("title").eq(create_post.title) & Attr(
            "created_at"
        ).between(now.start_of("day").isoformat("T"), now.end_of("day").isoformat("T"))
        if await self._repository.get_post(filter_expression):
            raise PostAlreadyExistsException(
                PostService.ERROR_MESSAGE_POST_ALREADY_EXISTS
            )
        data = create_post.model_dump()
        data["id"] = str(uuid.uuid4())
        data["created_at"] = now.to_iso8601_string()
        data["deleted_at"] = None
        data["slug"] = slugify(data["title"])
        data["updated_at"] = None
        await self._repository.create_post(data)
        return Post(**data)

    async def delete_post(self, post_uuid: str):
        post = await self._get_post_by_uuid(post_uuid)
        post.deleted_at = pendulum.now().to_iso8601_string()
        await self._repository.update_post(
            post_uuid, post.model_dump(exclude={"id"}), FilterExpressions.NOT_DELETED
        )
        self._logger.info(f"Post successfully deleted {post_uuid=}")

    async def get_all_posts(self, descending: bool = True) -> Page:
        items = await self._repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            ["id", "title", "meta", "published_at", "updated_at"],
        )
        posts = []
        for item in sorted(items, key=lambda i: i["published_at"], reverse=descending):
            posts.append(PostResponse(**item))
        return Page(data=posts)

    async def get_post(self, post_uuid: str) -> PostResponse:
        return await _item_to_response(
            (await self._get_post_by_uuid(post_uuid)).model_dump(), to_markdown=True
        )

    async def get_post_by_date_and_slug(
        self, year: int, month: int, day: int, slug: str
    ) -> PostResponse:
        start = pendulum.datetime(year, month, day)
        end = start.end_of("day")
        start.to_datetime_string()
        filter_expression = (
            FilterExpressions.NOT_DELETED
            & Attr("published_at").between(start.isoformat("T"), end.isoformat("T"))
            & Attr("slug").eq(slug)
        )
        item = await self._repository.get_post(filter_expression)
        if item is None:
            self._logger.warning(f"Failed to get post {filter_expression=}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        return await _item_to_response(item, to_markdown=True)

    async def get_posts(self, exclusive_start_key: Optional[str] = None) -> Page:
        response = await self._repository.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            exclusive_start_key,
            ["id", "title", "meta", "published_at", "updated_at"],
        )
        posts = []
        for item in response[1]:
            posts.append(PostResponse(**item))
        return Page(exclusive_start_key=response[0], data=posts)

    async def update_post(self, post_uuid: str, update_post: UpdatePost):
        item = await self._repository.get_post_by_uuid(
            post_uuid, FilterExpressions.NOT_DELETED
        )
        if item is None:
            self._logger.warning(f"Post was not found by UUID {post_uuid=}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        item.update(update_post.model_dump(exclude_unset=True))
        post = Post(**item)
        post.updated_at = pendulum.now().to_iso8601_string()
        await self._repository.update_post(
            post_uuid, post.model_dump(exclude={"id"}), FilterExpressions.NOT_DELETED
        )
        self._logger.info(f"Post successfully updated {post_uuid=}")

    async def get_archive(self) -> dict[str, int]:
        items = await self._repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            ["id", "published_at"],
        )
        archive = {}
        if items:
            dates = list(map(lambda x: x["published_at"], items))
            for dt in pendulum.interval(
                pendulum.parse(min(dates)).start_of("month"),
                pendulum.parse(max(dates)).end_of("month"),
            ).range("months"):
                result = list(
                    filter(
                        lambda x, start=dt, end=dt.end_of("month"): start
                        <= pendulum.parse(x)
                        <= end,
                        dates,
                    )
                )
                archive[dt.format("YYYY-MM")] = len(result)
        return archive
