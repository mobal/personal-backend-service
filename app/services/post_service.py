import uuid
from typing import Any

import bleach
import markdown
import pendulum
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from pendulum import DateTime
from slugify import slugify

from app.exceptions import PostAlreadyExistsException, PostNotFoundException
from app.models.post import Post
from app.models.response import (
    Page,
    Post as PostResponse,
)
from app.repositories.post_repository import PostRepository


class FilterExpressions:
    NOT_DELETED = Attr("deleted_at").eq(None) | Attr("deleted_at").not_exists()
    PUBLISHED = Attr("published_at").ne(None)


class PostService:
    ERROR_POST_EXISTS = "There is already a post with this title"
    ERROR_POST_NOT_FOUND = "The requested post was not found"

    def __init__(self):
        self._logger = Logger()
        self._repo = PostRepository()

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._repo.get_post_by_uuid(post_uuid)
        if not item or item.get("deleted_at") is not None:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return Post(**item)

    def _post_to_response(self, post_data: dict[str, Any]) -> PostResponse:
        html = markdown.markdown(post_data["content"])
        allowed_tags = bleach.ALLOWED_TAGS | {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "br",
            "hr",
            "ul",
            "ol",
            "li",
            "pre",
            "code",
            "blockquote",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
            "a",
            "strong",
            "em",
            "u",
            "s",
            "del",
            "ins",
            "sup",
            "sub",
            "div",
            "span",
        }
        allowed_attributes = {
            "a": ["href", "title", "rel"],
            "img": ["src", "alt", "title", "width", "height"],
            "*": ["class"],
        }
        sanitized = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True,
        )
        post_data["content"] = sanitized
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
        post_path = f"{now.year}/{now.month}/{now.day}/{slugify(data['title'])}"
        data.update(
            {
                "id": str(uuid.uuid4()),
                "post_path": post_path,
                "created_at": now.to_iso8601_string(),
                "deleted_at": None,
                "slug": slugify(data["title"]),
                "updated_at": None,
            }
        )
        self._repo.create_post(data)
        return Post(**data)

    def delete_post(self, post_uuid: str):
        now = pendulum.now().to_iso8601_string()
        try:
            self._repo.update_post(
                post_uuid,
                {"deleted_at": now, "updated_at": now},
                Attr("id").exists() & FilterExpressions.NOT_DELETED,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
            raise
        self._logger.info(f"Post deleted: {post_uuid=}")

    def get_post(self, post_uuid: str) -> PostResponse:
        return self._post_to_response(self.get_post_by_uuid(post_uuid).model_dump())

    def get_by_post_path(self, post_path: str) -> PostResponse:
        post = self._repo.get_post_by_post_path(
            post_path, FilterExpressions.NOT_DELETED
        )
        if not post:
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

    def update_post(self, post_uuid: str, update_data: dict[str, Any]):
        update_data["updated_at"] = pendulum.now().to_iso8601_string()
        try:
            self._repo.update_post(
                post_uuid,
                update_data,
                Attr("id").exists() & FilterExpressions.NOT_DELETED,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
            raise
        self._logger.info(f"Post updated: {post_uuid=}")

    def _sort_dates_and_group_by_month(
        self, dates: list[DateTime], max_results: int = 100
    ) -> dict[str, int]:
        sorted_dates = sorted(dates)
        archive = {}
        current_month = None
        count = 0

        for date in sorted_dates:
            if count >= max_results:
                break

            month_key = date.strftime("%Y-%m")

            if current_month != month_key:
                if current_month is not None:
                    archive[current_month] = count
                current_month = month_key
                count = 1
            else:
                count += 1

        if current_month is not None:
            archive[current_month] = count

        return archive

    def get_archive(
        self,
        max_results: int = 100,
    ) -> dict[str, int]:
        posts = self._repo.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            ["id", "published_at"],
        )
        if not posts:
            return {}

        dates = [pendulum.parse(post["published_at"]) for post in posts]
        return self._sort_dates_and_group_by_month(dates, max_results) if dates else {}

    def get_archive_paginated(
        self,
        exclusive_start_key: str | None = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get archive with pagination support."""
        last_key, posts = self._repo.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            {"id": exclusive_start_key} if exclusive_start_key else None,
            ["id", "published_at"],
        )
        if not posts:
            return {
                "archive": {},
                "count": 0,
                "exclusive_start_key": exclusive_start_key,
                "last_evaluated_key": None,
            }

        dates = [pendulum.parse(post["published_at"]) for post in posts]
        archive = (
            self._sort_dates_and_group_by_month(dates, max_results) if dates else {}
        )

        return {
            "archive": archive,
            "count": len(posts),
            "exclusive_start_key": exclusive_start_key,
            "last_evaluated_key": last_key,
        }
