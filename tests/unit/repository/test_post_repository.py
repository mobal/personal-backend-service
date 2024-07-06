import uuid
from collections import Counter
from random import randint

import pendulum
import pytest
from boto3.dynamodb.conditions import AttributeBase

from app.models.post import Post
from app.repositories.post_repository import PostRepository


@pytest.mark.asyncio
class TestPostRepository:
    async def test_successfully_create_post(
        self,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        post_dict = posts[0].model_dump()
        post_dict["id"] = str(uuid.uuid4())

        await post_repository.create_post(post_dict)

        response = posts_table.get_item(Key={"id": post_dict["id"]})

        assert response["Item"] == post_dict

    async def test_successfully_get_all_posts(
        self,
        filter_expression: AttributeBase,
        posts: list[Post],
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
        posts: list[Post],
        post_repository: PostRepository,
    ):
        fields = ["id", "title", "meta", "published_at"]
        items = await post_repository.get_all_posts(filter_expression, fields)

        assert len(items) == len(posts)
        for item in items:
            assert Counter(fields) == Counter(item.keys())

    async def test_successfully_get_all_posts_with_using_last_evaluated_key(
        self,
        faker,
        filter_expression: AttributeBase,
        make_post,
        post_repository: PostRepository,
        posts: list[Post],
        posts_table,
    ):
        with posts_table.batch_writer() as batch:
            for _ in range(100):
                long_sized_post = make_post()
                long_sized_post.content = faker.text(randint(10_000, 25_000))
                batch.put_item(Item=long_sized_post.model_dump())

        items = await post_repository.get_all_posts(
            filter_expression, list(long_sized_post.model_fields.keys())
        )

        assert len(posts) + 100 == len(items)

    async def test_successfully_get_post_by_uuid(
        self,
        filter_expression: AttributeBase,
        posts: list[Post],
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
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        now = pendulum.now()
        data = {"content": "Updated content", "updated_at": now.to_iso8601_string()}

        await post_repository.update_post(posts[0].id, data, filter_expression)

        response = posts_table.get_item(Key={"id": posts[0].id})
        assert response["Item"]["updated_at"] is not None
        assert (
            posts[0].model_dump(exclude={"content", "updated_at"}).items()
            <= response["Item"].items()
        )

    async def test_successfully_get_item_count(
        self, posts: list[Post], post_repository: PostRepository
    ):
        assert len(posts) == await post_repository.item_count()

    async def test_successfully_count_all_posts(
        self,
        filter_expression: AttributeBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        assert len(posts) == await post_repository.count_all_posts(filter_expression)

    async def test_successfully_count_all_posts_with_using_last_evaluated_key(
        self,
        faker,
        filter_expression: AttributeBase,
        make_post,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        with posts_table.batch_writer() as batch:
            for _ in range(100):
                long_sized_post = make_post()
                long_sized_post.content = faker.text(randint(10_000, 25_000))
                batch.put_item(Item=long_sized_post.model_dump())

        assert len(posts) + 100 == await post_repository.count_all_posts(
            filter_expression
        )
