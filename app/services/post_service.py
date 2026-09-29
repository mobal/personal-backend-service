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
ALLOWED_POST_TAGS = bleach.ALLOWED_TAGS | {
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
ALLOWED_POST_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "*": ["class"],
}


def normalize_post_path(post_path: str) -> str | None:
    """Return post_path with zero-padded month/day (e.g. 2026/09/09/slug)."""
    if (match := POST_PATH_RE.match(post_path)) is None:
        return None
    year, month, day, slug = match.groups()
    return f"{int(year):04d}/{int(month):02d}/{int(day):02d}/{slug}"


class PostService:
    ERROR_POST_EXISTS = "There is already a post with this title"
    ERROR_POST_NOT_FOUND = "The requested post was not found"

    def __init__(self, post_repository: PostRepository):
        self._logger = Logger()
        self._post_repository = post_repository

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._post_repository.get_post_by_uuid(post_uuid)
        if not item or item.get("deleted_at") is not None:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return Post(**item)

    def _post_to_response(self, post_data: dict[str, Any]) -> PostResponse:
        post_data["content"] = self._render_content(post_data["content"])
        self._attach_download_urls(post_data)
        if post_data.get("post_path"):
            post_data["post_path"] = normalize_post_path(post_data["post_path"])
        return PostResponse(**post_data)

    @staticmethod
    def _render_content(content: str) -> str:
        html = markdown.markdown(content)
        return bleach.clean(
            html,
            tags=ALLOWED_POST_TAGS,
            attributes=ALLOWED_POST_ATTRIBUTES,
            strip=True,
        )

    def _attach_download_urls(self, post_data: dict[str, Any]) -> None:
        if post_data.get("attachments"):
            post_data["attachments"] = [
                attachment
                | {
                    "url": (
                        f"/api/v1/posts/{post_data['id']}/attachments/"
                        f"{attachment['id']}/download"
                    )
                }
                for attachment in post_data["attachments"]
            ]

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
                "attachments": [],
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

    def get_published_post_by_uuid(self, post_uuid: str) -> Post:
        post = self._post_repository.get_post_by_uuid(post_uuid)
        if (
            not post
            or post.get("deleted_at") is not None
            or not post.get("published_at")
            or datetime.fromisoformat(post["published_at"]) > datetime.now(UTC)
        ):
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return Post(**post)

    def get_post(self, post_uuid: str) -> PostResponse:
        return self._post_to_response(
            self.get_published_post_by_uuid(post_uuid).model_dump()
        )

    def get_by_post_path(self, post_path: str) -> PostResponse:
        filter_expression = (
            FilterExpressions.NOT_DELETED & FilterExpressions.published()
        )
        post = self._find_post_by_path(post_path, filter_expression)
        if not post:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return self._post_to_response(post)

    def _find_post_by_path(
        self, post_path: str, filter_expression: Any
    ) -> dict[str, Any] | None:
        for candidate in self._post_path_candidates(post_path):
            post = self._post_repository.get_post_by_post_path(
                candidate, filter_expression
            )
            if post:
                return post
        return None

    @staticmethod
    def _post_path_candidates(post_path: str) -> list[str]:
        candidates = [post_path]
        normalized = normalize_post_path(post_path)
        if normalized and normalized != post_path:
            candidates.append(normalized)

        # Older posts may have unpadded month and day values in storage.
        if match := POST_PATH_RE.match(post_path):
            year, month, day, slug = match.groups()
            unpadded = f"{int(year)}/{int(month)}/{int(day)}/{slug}"
            if unpadded not in candidates:
                candidates.append(unpadded)
        return candidates

    def get_posts(self, exclusive_start_key: str | None = None) -> Page:
        last_key, posts = self._post_repository.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            {"id": exclusive_start_key} if exclusive_start_key else None,
            ["id", "title", "meta", "post_path", "published_at", "updated_at"],
        )
        for post in posts:
            self._attach_download_urls(post)
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

    def append_attachment(self, post_uuid: str, attachment: dict[str, Any]) -> None:
        self._post_repository.append_attachment(post_uuid, attachment)

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

        return self._archive_from_posts(posts, max_results)

    def _archive_from_posts(
        self, posts: list[dict[str, Any]], max_results: int
    ) -> dict[str, int]:
        dates = [datetime.fromisoformat(post["published_at"]) for post in posts]
        return self._sort_dates_and_group_by_month(dates, max_results)

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

        return {
            "archive": self._archive_from_posts(posts, max_results),
            "count": len(posts),
            "exclusive_start_key": exclusive_start_key,
            "last_evaluated_key": last_key,
        }
