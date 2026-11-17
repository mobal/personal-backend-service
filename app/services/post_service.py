import base64
import binascii
import json
import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import bleach
import markdown
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from slugify import slugify

from app.exceptions import (
    InvalidPageCursorException,
    InvalidPostTitleException,
    PostAlreadyExistsException,
    PostNotFoundException,
)
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


# The listing is sorted in memory over every published post, so it can order
# them globally; a blog this size keeps everything on one page.
POSTS_PAGE_SIZE = 100

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


def render_markdown(content: str) -> str:
    """Render Markdown to HTML that is safe to embed in a page or a feed."""
    return bleach.clean(
        markdown.markdown(content),
        tags=ALLOWED_POST_TAGS,
        attributes=ALLOWED_POST_ATTRIBUTES,
        strip=True,
    )


class PostService:
    ERROR_POST_EXISTS = "There is already a post with this title"
    ERROR_POST_PATH_EXISTS = "There is already a post with this date and slug"
    ERROR_TITLE_WITHOUT_SLUG = "The title must contain at least one letter or digit"
    ERROR_POST_NOT_FOUND = "The requested post was not found"
    ERROR_INVALID_CURSOR = "The pagination cursor is not valid"

    def __init__(self, post_repository: PostRepository):
        self._logger = Logger()
        self._post_repository = post_repository

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._post_repository.get_post_by_uuid(post_uuid)
        if not item or item.get("deleted_at") is not None:
            raise PostNotFoundException(self.ERROR_POST_NOT_FOUND)
        return Post(**item)

    def _post_to_response(self, post_data: dict[str, Any]) -> PostResponse:
        post_data["content"] = render_markdown(post_data["content"])
        self._attach_download_urls(post_data)
        if post_data.get("post_path"):
            post_data["post_path"] = normalize_post_path(post_data["post_path"])
        return PostResponse(**post_data)

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
        slug, post_path = self._slug_and_post_path(data["title"], now)
        data.update(
            {
                "id": str(uuid.uuid4()),
                "post_path": post_path,
                "created_at": now.isoformat(),
                "deleted_at": None,
                "attachments": [],
                "slug": slug,
                "updated_at": None,
            }
        )
        self._post_repository.create_post(data)
        return Post(**data)

    def _slug_and_post_path(
        self, title: str, created_at: datetime, post_uuid: str | None = None
    ) -> tuple[str, str]:
        """Derive the public path and make sure no other post already owns it.

        Different titles can share a slug ("Hello World", "Hello, World!"), and
        the path lookup returns a single post, so a second owner would shadow
        the first.
        """
        slug = slugify(title)
        if not slug:
            raise InvalidPostTitleException(self.ERROR_TITLE_WITHOUT_SLUG)
        post_path = f"{created_at:%Y/%m/%d}/{slug}"
        owner = self._post_repository.get_post_by_post_path(
            post_path, FilterExpressions.NOT_DELETED
        )
        if owner and owner.get("id") != post_uuid:
            raise PostAlreadyExistsException(self.ERROR_POST_PATH_EXISTS)
        return slug, post_path

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

    def get_readable_post_by_uuid(
        self, post_uuid: str, include_unpublished: bool = False
    ) -> Post:
        """Published posts for everyone; drafts and scheduled ones on request."""
        if include_unpublished:
            return self.get_post_by_uuid(post_uuid)
        return self.get_published_post_by_uuid(post_uuid)

    def get_post(
        self, post_uuid: str, include_unpublished: bool = False
    ) -> PostResponse:
        return self._post_to_response(
            self.get_readable_post_by_uuid(post_uuid, include_unpublished).model_dump()
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

    @staticmethod
    def _listing_position(published_at: str, post_id: str) -> tuple[datetime, str]:
        parsed = datetime.fromisoformat(published_at)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed, post_id

    @staticmethod
    def _encode_cursor(post: dict[str, Any]) -> str:
        raw = json.dumps([post["published_at"], post["id"]]).encode()
        return base64.urlsafe_b64encode(raw).decode()

    def _decode_cursor(self, cursor: str) -> tuple[datetime, str]:
        try:
            published_at, post_id = json.loads(base64.urlsafe_b64decode(cursor))
            return self._listing_position(published_at, post_id)
        except (binascii.Error, ValueError, TypeError) as exc:
            raise InvalidPageCursorException(self.ERROR_INVALID_CURSOR) from exc

    def get_posts(self, exclusive_start_key: str | None = None) -> Page:
        after = (
            self._decode_cursor(exclusive_start_key) if exclusive_start_key else None
        )
        posts = self._post_repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            ["id", "title", "meta", "post_path", "published_at", "updated_at"],
        )
        # A table scan returns items in hash order and splits them into 1 MB
        # pages (counted on the stored items, whatever is projected), so the
        # order is established here, over all posts. The cursor is a position
        # in that order, not a post: it stays valid when its post is removed.
        posts.sort(
            key=lambda post: self._listing_position(post["published_at"], post["id"]),
            reverse=True,
        )
        if after is not None:
            posts = [
                post
                for post in posts
                if self._listing_position(post["published_at"], post["id"]) < after
            ]
        page, rest = posts[:POSTS_PAGE_SIZE], posts[POSTS_PAGE_SIZE:]
        for post in page:
            self._attach_download_urls(post)
            if post.get("post_path"):
                post["post_path"] = normalize_post_path(post["post_path"])
        return Page(
            exclusive_start_key=self._encode_cursor(page[-1]) if rest else None,
            posts=[PostResponse(**post) for post in page],
        )

    def get_published_posts(self) -> list[Post]:
        posts = self._post_repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            [
                "id",
                "author",
                "title",
                "content",
                "post_path",
                "published_at",
                "created_at",
                "meta",
                "slug",
                "tags",
            ],
        )
        return [Post(**post) for post in posts]

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

        update_data["slug"], update_data["post_path"] = self._slug_and_post_path(
            update_data["title"],
            datetime.fromisoformat(current["created_at"]),
            post_uuid,
        )

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

    def get_archive(self) -> dict[str, int]:
        posts = self._post_repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.published(),
            ["id", "published_at"],
        )
        months = Counter(
            datetime.fromisoformat(post["published_at"]).strftime("%Y-%m")
            for post in posts
        )
        return dict(sorted(months.items()))
