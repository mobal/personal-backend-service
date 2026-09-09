import re
import uuid
from datetime import UTC, datetime
from typing import Any

import bleach
import markdown
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
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

    @staticmethod
    def published() -> Any:
        return Attr("published_at").lte(datetime.now(UTC).isoformat())


POST_PATH_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})/(.+)$")


def normalize_post_path(post_path: str) -> str | None:
    """Return post_path with zero-padded month/day (e.g. 2026/09/09/slug)."""
    if (match := POST_PATH_RE.match(post_path)) is None:
        return None
    year, month, day, slug = match.groups()
    return f"{int(year):04d}/{int(month):02d}/{int(day):02d}/{slug}"


class PostService:
    ERROR_POST_EXISTS = "There is already a post with this title"
    ERROR_POST_NOT_FOUND = "The requested post was not found"

    def __init__(
        self,
        post_repository: PostRepository,
    ):
        self._logger = Logger()
        self._post_repository = post_repository

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._post_repository.get_post_by_uuid(post_uuid)
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
        if post_data.get("post_path"):
            post_data["post_path"] = normalize_post_path(post_data["post_path"])
        return PostResponse(**post_data)

    def create_post(self, data: dict[str, Any]) -> Post:
        now = datetime.now(UTC)
        if self._post_repository.get_post_by_title(
            data["title"], FilterExpressions.NOT_DELETED
        ):
            raise PostAlreadyExistsException(self.ERROR_POST_EXISTS)
        post_path = f"{now:%Y/%m/%d}/{slugify(data['title'])}"
        data.update(
            {
                "id": str(uuid.uuid4()),
                "post_path": post_path,
                "created_at": now.isoformat(),
                "deleted_at": None,
                "slug": slugify(data["title"]),
                "updated_at": None,
            }
        )
        self._post_repository.create_post(data)
        return Post(**data)

    def delete_post(self, post_uuid: str):
        now = datetime.now(UTC).isoformat()
        try:
            self._post_repository.update_post(
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
        post = self._post_repository.get_post_by_uuid(post_uuid)
        if (
            not post
            or post.get("deleted_at") is not None
            or not post.get("published_at")
            or datetime.fromisoformat(post["published_at"]) > datetime.now(UTC)
        ):
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return self._post_to_response(post)

    def get_by_post_path(self, post_path: str) -> PostResponse:
        filter_expression = (
            FilterExpressions.NOT_DELETED & FilterExpressions.published()
        )
        candidates = [post_path]
        normalized = normalize_post_path(post_path)
        # Posts created before zero-padding was introduced store unpadded
        # month/day, so also try the unpadded form of the path.
        if normalized and normalized != post_path:
            candidates.append(normalized)
        if (match := POST_PATH_RE.match(post_path)) is not None:
            year, month, day, slug = match.groups()
            unpadded = f"{int(year)}/{int(month)}/{int(day)}/{slug}"
            if unpadded not in candidates:
                candidates.append(unpadded)
        post = None
        for candidate in candidates:
            post = self._post_repository.get_post_by_post_path(
                candidate, filter_expression
            )
            if post:
                break
        if not post:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return self._post_to_response(post)

    def get_posts(self, exclusive_start_key: str | None = None) -> Page:
        last_key, posts = self._post_repository.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            {"id": exclusive_start_key} if exclusive_start_key else None,
            ["id", "title", "meta", "post_path", "published_at", "updated_at"],
        )
        for post in posts:
            if post.get("post_path"):
                post["post_path"] = normalize_post_path(post["post_path"])
        return Page(
            exclusive_start_key=last_key,
            posts=[PostResponse(**post) for post in posts],
        )

    def update_post(self, post_uuid: str, update_data: dict[str, Any]):
        if "title" in update_data:
            self._prepare_title_update(post_uuid, update_data)

        update_data["updated_at"] = datetime.now(UTC).isoformat()
        try:
            self._post_repository.update_post(
                post_uuid,
                update_data,
                Attr("id").exists() & FilterExpressions.NOT_DELETED,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
            raise
        self._logger.info(f"Post updated: {post_uuid=}")

    def _prepare_title_update(self, post_uuid: str, update_data: dict[str, Any]):
        current = self._post_repository.get_post_by_uuid(post_uuid)
        if not current or current.get("deleted_at") is not None:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)

        if update_data["title"] == current.get("title"):
            return

        duplicate = self._post_repository.get_post_by_title(
            update_data["title"], FilterExpressions.NOT_DELETED
        )
        if duplicate and duplicate.get("id") != post_uuid:
            raise PostAlreadyExistsException(self.ERROR_POST_EXISTS)

        slug = slugify(update_data["title"])
        created_at = datetime.fromisoformat(current["created_at"])
        update_data["slug"] = slug
        update_data["post_path"] = f"{created_at:%Y/%m/%d}/{slug}"

    def update_publish_state(
        self,
        post_uuid: str,
        status: str,
        attempted_at: str,
        error: str | None = None,
    ):
        now = datetime.now(UTC).isoformat()
        try:
            self._post_repository.update_post(
                post_uuid,
                {
                    "publish_status": status,
                    "publish_attempted_at": attempted_at,
                    "publish_error": error,
                    "updated_at": now,
                },
                Attr("id").exists() & FilterExpressions.NOT_DELETED,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
            raise

    def _sort_dates_and_group_by_month(
        self, dates: list[datetime], max_results: int = 100
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
        posts = self._post_repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            ["id", "published_at"],
        )
        if not posts:
            return {}

        dates = [datetime.fromisoformat(post["published_at"]) for post in posts]
        return self._sort_dates_and_group_by_month(dates, max_results) if dates else {}

    def get_archive_paginated(
        self,
        exclusive_start_key: str | None = None,
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Get archive with pagination support."""
        last_key, posts = self._post_repository.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
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

        dates = [datetime.fromisoformat(post["published_at"]) for post in posts]
        archive = (
            self._sort_dates_and_group_by_month(dates, max_results) if dates else {}
        )

        return {
            "archive": archive,
            "count": len(posts),
            "exclusive_start_key": exclusive_start_key,
            "last_evaluated_key": last_key,
        }
