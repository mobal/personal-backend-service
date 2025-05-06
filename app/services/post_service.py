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
    ERROR_MESSAGE_POST_ALREADY_EXISTS: str = "There is already a post with this title"
    ERROR_MESSAGE_POST_WAS_NOT_FOUND: str = "The requested post was not found"

    def __init__(self):
        self._logger = Logger(utc=True)
        self._post_repository = PostRepository()

    def get_post_by_uuid(self, post_uuid: str) -> Post:
        item = self._post_repository.get_post_by_uuid(
            post_uuid, FilterExpressions.NOT_DELETED
        )
        if item is None:
            self._logger.warning(f"Post was not found with UUID {post_uuid=}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        return Post(**item)

    def _post_to_response(self, post_dict: dict[str, Any]) -> PostResponse:
        post_dict["content"] = markdown.markdown(post_dict["content"])
        return PostResponse(**post_dict)

    def create_post(self, create_data: dict[str, Any]) -> Post:
        now = pendulum.now()
        if self._post_repository.get_post_by_title(
            create_data["title"],
            Attr("created_at").between(
                now.start_of("day").isoformat("T"), now.end_of("day").isoformat("T")
            ),
        ):
            raise PostAlreadyExistsException(
                PostService.ERROR_MESSAGE_POST_ALREADY_EXISTS
            )
        slug = slugify(create_data["title"])
        create_data["id"] = str(uuid.uuid4())
        create_data["post_path"] = f"{now.year}/{now.month}/{now.day}/{slug}"
        create_data["created_at"] = now.to_iso8601_string()
        create_data["deleted_at"] = None
        create_data["slug"] = slug
        create_data["updated_at"] = None
        self._post_repository.create_post(create_data)
        return Post(**create_data)

    def delete_post(self, post_uuid: str):
        post = self.get_post_by_uuid(post_uuid)
        post.deleted_at = pendulum.now().to_iso8601_string()
        self._post_repository.update_post(
            post_uuid,
            post.model_dump(exclude={"id"}),
            FilterExpressions.NOT_DELETED,
        )
        self._logger.info(f"Post successfully deleted {post_uuid=}")

    def get_post(self, post_uuid: str) -> PostResponse:
        return self._post_to_response((self.get_post_by_uuid(post_uuid)).model_dump())

    def get_by_post_path(self, post_path: str) -> PostResponse:
        post = self._post_repository.get_post_by_post_path(
            post_path, FilterExpressions.NOT_DELETED
        )
        if post is None:
            self._logger.warning(f"Failed to get post {FilterExpressions.NOT_DELETED}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        return self._post_to_response(post)

    def get_posts(self, exclusive_start_key: str | None = None) -> Page:
        last_evaluated_key, posts = self._post_repository.get_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            {"id": exclusive_start_key} if exclusive_start_key else None,
            ["id", "title", "meta", "published_at", "updated_at"],
        )
        post_responses = []
        for post in posts:
            post_responses.append(PostResponse(**post))
        return Page(exclusive_start_key=last_evaluated_key, posts=post_responses)

    def update_post(self, post_uuid: str, update_data: dict[str, Any]):
        post = self._post_repository.get_post_by_uuid(
            post_uuid, FilterExpressions.NOT_DELETED
        )
        if post is None:
            self._logger.warning(f"Post was not found by UUID {post_uuid=}")
            raise PostNotFoundException(PostService.ERROR_MESSAGE_POST_WAS_NOT_FOUND)
        post.update(update_data)
        post["updated_at"] = pendulum.now().to_iso8601_string()
        post.pop("id")
        self._post_repository.update_post(
            post_uuid,
            post,
            FilterExpressions.NOT_DELETED,
        )
        self._logger.info(f"Post successfully updated {post_uuid=}")

    def get_archive(self) -> dict[str, int]:
        posts = self._post_repository.get_all_posts(
            FilterExpressions.NOT_DELETED & FilterExpressions.PUBLISHED,
            ["id", "published_at"],
        )
        archive = {}
        if posts:
            dates: list = [pendulum.parse(item["published_at"]) for item in posts]
            for dt in pendulum.interval(
                min(dates).start_of("month"), max(dates).end_of("month")
            ).range("months"):
                archive[dt.format("YYYY-MM")] = sum(
                    1
                    for date in dates
                    if dt.start_of("month") <= date <= dt.end_of("month")
                )
        return archive
