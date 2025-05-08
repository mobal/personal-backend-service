import uuid
from collections import Counter
from random import randint

import pendulum
from boto3.dynamodb.conditions import ConditionBase

from app.models.post import Post
from app.repositories.post_repository import PostRepository

LARGE_SIZED_POST_MAX_LENGTH = 25_000
LARGE_SIZED_POST_MIN_LENGTH = 10_000
MAX_NUMBER_OF_LARGE_SIZED_POSTS = 100


class TestPostRepository:
    def test_successfully_create_post(
        self,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        post_dict = posts[0].model_dump()
        post_dict["id"] = str(uuid.uuid4())

        post_repository.create_post(post_dict)

        response = posts_table.get_item(Key={"id": post_dict["id"]})

        assert response["Item"] == post_dict

    def test_successfully_get_all_posts(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        items = post_repository.get_all_posts(
            filter_expression, list(posts[0].model_fields.keys())
        )

        assert len(items) == len(posts)
        assert any(post.model_dump() == items[0] for post in posts)

    def test_successfully_get_all_posts_with_fields_filter(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        fields = ["id", "title", "meta", "published_at"]
        items = post_repository.get_all_posts(filter_expression, fields)

        assert len(items) == len(posts)
        for item in items:
            assert Counter(fields) == Counter(item.keys())

    def test_successfully_get_all_posts_with_using_last_evaluated_key(
        self,
        faker,
        filter_expression: ConditionBase,
        make_post,
        post_repository: PostRepository,
        posts: list[Post],
        posts_table,
    ):
        with posts_table.batch_writer() as batch:
            for _ in range(MAX_NUMBER_OF_LARGE_SIZED_POSTS):
                long_sized_post = make_post()
                long_sized_post.content = faker.text(
                    randint(LARGE_SIZED_POST_MIN_LENGTH, LARGE_SIZED_POST_MAX_LENGTH)
                )
                batch.put_item(Item=long_sized_post.model_dump())

        items = post_repository.get_all_posts(
            filter_expression, list(long_sized_post.model_fields.keys())
        )

        assert len(posts) + MAX_NUMBER_OF_LARGE_SIZED_POSTS == len(items)

    def test_successfully_get_post_by_uuid(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        item = post_repository.get_post_by_uuid(posts[0].id, filter_expression)

        assert posts[0].model_dump() == item

    def test_fail_to_get_post_by_uuid(
        self,
        filter_expression: ConditionBase,
        post_repository: PostRepository,
    ):
        post_uuid = str(uuid.uuid4())

        assert post_repository.get_post_by_uuid(post_uuid, filter_expression) is None

    def test_successfully_update_post(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        now = pendulum.now()
        data = {"content": "Updated content", "updated_at": now.to_iso8601_string()}

        post_repository.update_post(posts[0].id, data, filter_expression)

        response = posts_table.get_item(Key={"id": posts[0].id})
        assert response["Item"]["updated_at"] is not None
        assert (
            posts[0].model_dump(exclude={"content", "updated_at"}).items()
            <= response["Item"].items()
        )

    def test_successfully_get_item_count(
        self, posts: list[Post], post_repository: PostRepository
    ):
        assert len(posts) == post_repository.item_count()

    def test_successfully_count_all_posts(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        assert len(posts) == post_repository.count_all_posts(filter_expression)

    def test_successfully_count_all_posts_with_using_last_evaluated_key(
        self,
        faker,
        filter_expression: ConditionBase,
        make_post,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        with posts_table.batch_writer() as batch:
            for _ in range(MAX_NUMBER_OF_LARGE_SIZED_POSTS):
                long_sized_post = make_post()
                long_sized_post.content = faker.text(
                    randint(LARGE_SIZED_POST_MIN_LENGTH, LARGE_SIZED_POST_MAX_LENGTH)
                )
                batch.put_item(Item=long_sized_post.model_dump())

        assert len(
            posts
        ) + MAX_NUMBER_OF_LARGE_SIZED_POSTS == post_repository.count_all_posts(
            filter_expression
        )

    def test_successfully_get_post_by_path(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        item = post_repository.get_post_by_post_path(
            posts[0].post_path, filter_expression
        )

        assert item == posts[0].model_dump()

    def test_successfully_get_post_by_title(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        item = post_repository.get_post_by_title(posts[0].title, filter_expression)

        assert item == posts[0].model_dump()

    def test_successfully_get_posts(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        last_evaluated_key, response = post_repository.get_posts(
            filter_expression, None, list(posts[0].model_fields.keys())
        )

        assert last_evaluated_key is None
        assert len(response) == len(posts)

    def test_successfully_get_posts_without_fields(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        last_evaluated_key, response = post_repository.get_posts(
            filter_expression, None
        )

        assert last_evaluated_key is None
        assert len(response) == len(posts)

    def test_successfully_get_posts_with_exclusive_start_key(
        self,
        filter_expression: ConditionBase,
        posts: list[Post],
        post_repository: PostRepository,
    ):
        last_evaluated_key, response = post_repository.get_posts(
            filter_expression, {"id": posts[0].id}
        )

        assert last_evaluated_key is None
        assert not any(post["id"] == posts[0].id for post in response)

    def test_successfully_get_posts_with_the_return_of_last_evaluated_key(
        self,
        faker,
        filter_expression: ConditionBase,
        make_post,
        posts: list[Post],
        post_repository: PostRepository,
        posts_table,
    ):
        with posts_table.batch_writer() as batch:
            for _ in range(MAX_NUMBER_OF_LARGE_SIZED_POSTS):
                long_sized_post = make_post()
                long_sized_post.content = faker.text(
                    randint(LARGE_SIZED_POST_MIN_LENGTH, LARGE_SIZED_POST_MAX_LENGTH)
                )
                batch.put_item(Item=long_sized_post.model_dump())

        last_evaluated_key, response = post_repository.get_posts(
            filter_expression, None
        )

        assert last_evaluated_key is not None
        assert response[-1]["id"] == last_evaluated_key
