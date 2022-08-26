import uuid

import pytest
from boto3.dynamodb.conditions import Key, Attr, AttributeBase
from starlette import status

from app.exception import PostNotFoundException
from app.models.post import Post
from app.repository.post import PostRepository


@pytest.mark.asyncio
class TestPostRepository:
    @pytest.fixture
    def dynamodb_table(self, dynamodb_resource):
        return dynamodb_resource.Table('test-posts')

    @pytest.fixture(autouse=True)
    def setup_table(self, dynamodb_resource, dynamodb_table, post_model: Post):
        dynamodb_resource.create_table(
            TableName='test-posts',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        )
        dynamodb_table.put_item(Item=post_model.dict())

    async def test_successfully_create_post(
        self, post_repository: PostRepository, post_dict: dict, post_model: Post
    ):
        post_dict['slug'] = f'some-random-title-{post_model.id}'
        result = await post_repository.create_post(post_dict)
        assert post_dict.get('author') == result.dict().get('author')
        assert post_dict.get('title') == result.dict().get('title')
        assert post_dict.get('content') == result.dict().get('content')
        assert post_dict.get('published_at') == result.dict().get('published_at')
        assert post_dict.get('tags') == result.dict().get('tags')
        assert post_dict.get('meta') == result.dict().get('meta')

    async def test_successfully_delete_post(
        self,
        dynamodb_table,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
        post_model: Post,
    ):
        await post_repository.delete_post(post_model.id, filter_expression)
        response = dynamodb_table.query(
            KeyConditionExpression=Key('id').eq(post_model.id),
            FilterExpression=Attr('deleted_at').eq(None),
        )
        assert response['Count'] == 0

    async def test_successfully_get_all_posts(
        self,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
        post_model: Post,
    ):
        result = await post_repository.get_all_posts(filter_expression)
        assert len(result) == 1
        assert post_model == result[0]

    async def test_successfully_get_all_posts_with_fields_filter(
        self,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
        post_model: Post,
    ):
        fields = ['id', 'title', 'meta', 'published_at']
        result = await post_repository.get_all_posts(
            filter_expression, ','.join(fields)
        )
        assert 1 == len(result)
        data = result[0].dict(exclude_none=True)
        assert 4 == len(data)
        for k, v in data.items():
            assert getattr(post_model, k) == v

    async def test_successfully_get_post_by_uuid(
        self,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
        post_model: Post,
    ):
        result = await post_repository.get_post_by_uuid(
            post_model.id, filter_expression
        )
        assert post_model == result

    async def test_fail_to_get_post_by_uuid_due_post_not_found_exception(
        self, filter_expression: AttributeBase, post_repository: PostRepository
    ):
        post_uuid = str(uuid.uuid4())
        with pytest.raises(PostNotFoundException) as excinfo:
            await post_repository.get_post_by_uuid(post_uuid, filter_expression)
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert f'Post was not found with UUID {post_uuid=}' == excinfo.value.detail

    async def test_successfully_update_post(
        self,
        dynamodb_table,
        filter_expression: AttributeBase,
        post_repository: PostRepository,
        post_model: Post,
    ):
        data = {'content': 'Updated content'}
        await post_repository.update_post(post_model.id, data, filter_expression)
        response = dynamodb_table.query(
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
        assert item['updated_at'] is not None
