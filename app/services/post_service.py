import uuid
from typing import Any

import markdown
import pendulum
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from slugify import slugify

from app.exceptions import PostAlreadyExistsException, PostNotFoundException
from app.models.post import Post
from app.models.response import Page
from app.models.response import Post as PostResponse
from app.repositories.post_repository import PostRepository


class FilterExpressions:
    NOT_DELETED = Attr("deleted_at").eq(None) | Attr("deleted_at").not_exists()
    PUBLISHED = Attr("published_at").ne(None)


class PostService:
    ERROR_POST_EXISTS = "There is already a post with this title"
    ERROR_POST_NOT_FOUND = "The requested post was not found"

    def __init__(self):
        self._logger = Logger(utc=True)
        self._repo = PostRepository()

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._repo.get_post_by_uuid(post_uuid, FilterExpressions.NOT_DELETED)
        if not item:
            self._logger.warning(f"Post not found: {post_uuid=}")
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return Post(**item)

    def _post_to_response(self, post_data: dict[str, Any]) -> PostResponse:
        post_data["content"] = markdown.markdown(post_data["content"])
        return PostResponse(**post_data)

    def create_post(self, data: dict[str, Any]) -> Post:
        now = pendulum.now()
        if self._repo.get_post_by_title(
            data["title"],
            Attr("created_at").between(
                now.start_of("day").isoformat("T"), now.end_of("day").isoformat("T")
            ),
        ):
            raise PostAlreadyExistsException(self.ERROR_POST_EXISTS)
        data.update(
            {
                "id": str(uuid.uuid4()),
                "post_path": f"{now.year}/{now.month}/{now.day}/{slugify(data['title'])}",
                "created_at": now.to_iso8601_string(),
                "deleted_at": None,
                "slug": slugify(data["title"]),
                "updated_at": None,
            }
        )
        self._repo.create_post(data)
        return Post(**data)

    def delete_post(self, post_uuid: str):
        post = self.get_post_by_uuid(post_uuid)
        post.deleted_at = pendulum.now().to_iso8601_string()
        self._repo.update_post(
            post_uuid, post.model_dump(exclude={"id"}), FilterExpressions.NOT_DELETED
        )
        self._logger.info(f"Post deleted: {post_uuid=}")

    def get_post(self, post_uuid: str) -> PostResponse:
        return self._post_to_response(self.get_post_by_uuid(post_uuid).model_dump())

    def get_by_post_path(self, post_path: str) -> PostResponse:
        post = self._repo.get_post_by_post_path(
            post_path, FilterExpressions.NOT_DELETED
        )
        if not post:
            self._logger.warning(f"Post not found: {post_path=}")
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return self._post_to_response(post)

    def get_posts(self, exclusive_start_key: str | None = None) -> Page:
        last_key, posts = self._repo.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            {"id": exclusive_start_key} if exclusive_start_key else None,
            ["id", "title", "meta", "published_at", "updated_at"],
        )
        return Page(
            exclusive_start_key=last_key,
            posts=[PostResponse(**post) for post in posts],
        )

    def update_post(self, post_uuid: str, data: dict[str, Any]):
        post = self._repo.get_post_by_uuid(post_uuid, FilterExpressions.NOT_DELETED)
        if not post:
            self._logger.warning(f"Post not found: {post_uuid=}")
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        post.update(data)
        post["updated_at"] = pendulum.now().to_iso8601_string()
        post.pop("id")
        self._repo.update_post(post_uuid, post, FilterExpressions.NOT_DELETED)
        self._logger.info(f"Post updated: {post_uuid=}")

    def get_archive(self) -> dict[str, int]:
        posts = self._repo.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            ["id", "published_at"],
        )
        if not posts:
            return {}
        dates = [pendulum.parse(post["published_at"]) for post in posts]
        archive = {}
        for dt in pendulum.interval(
            min(dates).start_of("month"), max(dates).end_of("month")
        ).range("months"):
            archive[dt.format("YYYY-MM")] = sum(
                1
                for date in dates
                if dt.start_of("month") <= date <= dt.end_of("month")
            )
        return archive
