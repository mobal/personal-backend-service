import uuid

import pendulum
import pytest
from boto3.dynamodb.conditions import Attr, AttributeBase, Key

from app.models.post import Post
from app.repositories.post import PostRepository


@pytest.mark.asyncio
class TestPostRepository:
    async def test_successfully_create_post(
        self,
        post_dict: dict,
        post_model: Post,
        post_repository: PostRepository,
        posts_table,
    ):
        post_dict['id'] = post_model.id
        post_dict['slug'] = f'some-random-title'
        await post_repository.create_post(post_model.dict())
        response = posts_table.query(KeyConditionExpression=Key('id').eq(post_model.id))
        assert 1 == response['Count']
        item = response['Items'][0]
        assert item == post_model.dict()

    async def test_successfully_get_all_posts(
        self,
        filter_expression: AttributeBase,
        post_model: Post,
        post_repository: PostRepository,
    ):
        items = await post_repository.get_all_posts(
            filter_expression, list(post_model.__fields__.keys())
        )
        assert len(items) == 1
        assert post_model == items[0]

    async def test_successfully_get_all_posts_with_fields_filter(
        self,
        filter_expression: AttributeBase,
        post_model: Post,
        post_repository: PostRepository,
    ):
        fields = ['id', 'title', 'meta', 'published_at']
        items = await post_repository.get_all_posts(filter_expression, fields)
        assert 1 == len(items)
        assert 4 == len(items[0])
        for k, v in items[0].items():
            assert getattr(post_model, k) == v

    async def test_successfully_get_post_by_uuid(
        self,
        filter_expression: AttributeBase,
        post_model: Post,
        post_repository: PostRepository,
    ):
        item = await post_repository.get_post_by_uuid(post_model.id, filter_expression)
        assert post_model.dict() == item

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
        post_model: Post,
        post_repository: PostRepository,
        posts_table,
    ):
        now = pendulum.now()
        data = {'content': 'Updated content', 'updated_at': now.to_iso8601_string()}
        await post_repository.update_post(post_model.id, data, filter_expression)
        response = posts_table.query(
            KeyConditionExpression=Key('id').eq(post_model.id),
            FilterExpression=Attr('deleted_at').eq(None),
        )
        assert response['Count'] == 1
        item = response['Items'][0]
        assert post_model.id == item['id']
        assert post_model.author == item['author']
        assert post_model.meta == item['meta']
        assert post_model.slug == item['slug']
        assert post_model.tags == item['tags']
        assert post_model.title == item['title']
        assert post_model.created_at == item['created_at']
        assert post_model.deleted_at == item['deleted_at']
        assert post_model.published_at == item['published_at']
        assert 'Updated content' == item['content']
        assert now.to_iso8601_string() == item['updated_at']

    async def test_successfully_get_post(
        self, post_model: Post, post_repository: PostRepository
    ):
        dt = pendulum.parse(post_model.published_at)
        filter_expression = Attr('deleted_at').eq(None) | Attr(
            'deleted_at'
        ).not_exists() & Attr('published_at').between(
            dt.start_of('day').isoformat('T'), dt.end_of('day').isoformat('T')
        ) & Attr(
            'slug'
        ).eq(
            post_model.slug
        )
        item = await post_repository.get_post(filter_expression)
        assert post_model.dict() == item

    async def test_fail_to_get_post(
        self, post_model: Post, post_repository: PostRepository
    ):
        dt = pendulum.parse(post_model.published_at).add(days=1)
        filter_expression = (
            (Attr('deleted_at').eq(None) | Attr('deleted_at').not_exists())
            & Attr('published_at').between(
                dt.start_of('day').isoformat('T'), dt.end_of('day').isoformat('T')
            )
            & Attr('slug').eq(post_model.slug)
        )
        assert await post_repository.get_post(filter_expression) is None

    async def test_successfully_get_item_count(self, post_repository: PostRepository):
        item_count = await post_repository.item_count()
        assert 1 == item_count

    async def test_successfully_count_all_posts(
        self,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
    ):
        count = await post_repository.count_all_posts(filter_expression)
        assert 1 == count
