import uuid
from collections import Counter
from typing import List

import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, AttributeBase, Key
from pydantic import BaseModel

from app.models.post import Post
from app.repositories.post import PostRepository


@pytest.mark.asyncio
class TestPostRepository:
    async def test_successfully_create_post(
        self,
        posts: List[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        post_dict = posts[0].model_dump()
        post_dict["id"] = str(uuid.uuid4())

        await post_repository.create_post(post_dict)

        response = posts_table.query(
            KeyConditionExpression=Key("id").eq(post_dict["id"])
        )
        assert 1 == response["Count"]
        item = response["Items"][0]
        assert item == post_dict

    async def test_successfully_get_all_posts(
        self,
        filter_expression: AttributeBase,
        posts: List[Post],
        post_repository: PostRepository,
    ):
        items = await post_repository.get_all_posts(
            filter_expression, list(posts[0].model_fields.keys())
        )
        assert len(items) == len(posts)
        assert any(post.model_dump() == items[0] for post in posts)

    async def test_successfully_get_all_posts_with_fields_filter(
        self,
        filter_expression: AttributeBase,
        posts: List[Post],
        post_repository: PostRepository,
    ):
        fields = ["id", "title", "meta", "published_at"]
        items = await post_repository.get_all_posts(filter_expression, fields)
        assert len(items) == len(posts)
        for item in items:
            assert Counter(fields) == Counter(item.keys())

    async def test_successfully_get_post_by_uuid(
        self,
        filter_expression: AttributeBase,
        posts: List[Post],
        post_repository: PostRepository,
    ):
        item = await post_repository.get_post_by_uuid(posts[0].id, filter_expression)
        assert posts[0].model_dump() == item

    async def test_fail_to_get_post_by_uuid(
        self,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
    ):
        post_uuid = str(uuid.uuid4())
        assert (
            await post_repository.get_post_by_uuid(post_uuid, filter_expression) is None
        )

    async def test_successfully_update_post(
        self,
        filter_expression: AttributeBase,
        posts: List[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        now = pendulum.now()
        data = {"content": "Updated content", "updated_at": now.to_iso8601_string()}
        await post_repository.update_post(posts[0].id, data, filter_expression)
        response = posts_table.query(
            KeyConditionExpression=Key("id").eq(posts[0].id),
            FilterExpression=Attr("deleted_at").eq(None),
        )
        assert response["Count"] == 1
        item = response["Items"][0]
        assert posts[0].id == item["id"]
        assert posts[0].author == item["author"]
        assert posts[0].meta.model_dump() == item["meta"]
        assert posts[0].slug == item["slug"]
        assert posts[0].tags == item["tags"]
        assert posts[0].title == item["title"]
        assert posts[0].created_at == item["created_at"]
        assert posts[0].deleted_at == item["deleted_at"]
        assert posts[0].published_at == item["published_at"]
        assert "Updated content" == item["content"]
        assert now.to_iso8601_string() == item["updated_at"]

    async def test_successfully_get_post(
        self, posts: List[Post], post_repository: PostRepository
    ):
        dt = pendulum.parse(posts[0].published_at)
        filter_expression = Attr("deleted_at").eq(None) | Attr(
            "deleted_at"
        ).not_exists() & Attr("published_at").between(
            dt.start_of("day").isoformat("T"), dt.end_of("day").isoformat("T")
        ) & Attr(
            "slug"
        ).eq(
            posts[0].slug
        )
        item = await post_repository.get_post(filter_expression)
        assert any(post.model_dump() == item for post in posts)

    async def test_fail_to_get_post(
        self, posts: List[Post], post_repository: PostRepository
    ):
        dt = pendulum.parse(posts[0].published_at).add(days=1)
        filter_expression = (
            (Attr("deleted_at").eq(None) | Attr("deleted_at").not_exists())
            & Attr("published_at").between(
                dt.start_of("day").isoformat("T"), dt.end_of("day").isoformat("T")
            )
            & Attr("slug").eq(posts[0].slug)
        )
        assert await post_repository.get_post(filter_expression) is None

    async def test_successfully_get_item_count(
        self, posts: List[Post], post_repository: PostRepository
    ):
        assert len(posts) == await post_repository.item_count()

    async def test_successfully_count_all_posts(
        self,
        filter_expression: AttributeBase,
        posts: List[Post],
        post_repository: PostRepository,
    ):
        assert len(posts) == await post_repository.count_all_posts(filter_expression)
