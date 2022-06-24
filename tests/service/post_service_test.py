import uuid

import pytest
from boto3.dynamodb.conditions import Key, Attr

from app.services.post import PostService


@pytest.mark.asyncio
class TestPostService:
    post = {'id': 'aad76f13-6d99-4e03-843a-aa03876e1197', 'author': 'mobal', 'content': 'Lorem ipsum',
            'created_at': '2022-06-23T20:49:17Z', 'deleted_at': None, 'published_at': None,
            'slug': 'lorem-ipsum', 'tags': ['lorem', 'ipsum'], 'title': 'Lorem ipsum', 'updated_at': None}

    @pytest.fixture
    def init_db(self, config, dynamodb_client) -> None:
        table_name = f'{config.app_stage}-posts'
        dynamodb_client.create_table(TableName=table_name,
                                     KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                                     AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                                     ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1})
        table = dynamodb_client.Table(table_name)
        table.put_item(Item=self.post)

    @pytest.fixture
    def post_service(self, init_db) -> PostService:
        return PostService()

    @pytest.fixture
    def table(self, config, dynamodb_client):
        return dynamodb_client.Table(f'{config.app_stage}-posts')

    async def test_successfully_create_post(self, post_service) -> None:
        data = {'author': 'root', 'title': 'Random title', 'content': 'Some random content',
                'published_at': '2022-06-23T20:49:17Z'}
        result = await post_service.create_post(data)
        assert result.id is not None
        assert result.created_at is not None
        assert result.deleted_at is None
        assert result.slug is not None
        assert result.tags is None
        assert result.updated_at is None
        assert data['author'] == result.author
        assert data['content'] == result.content
        assert data['published_at'] == result.published_at
        assert data['title'] == result.title

    async def test_successfully_delete_post(self, config, dynamodb_client, post_service, table):
        await post_service.delete_post(self.post['id'])
        response = table.query(
            KeyConditionExpression=Key('id').eq(self.post['id']),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        assert response['Count'] == 0

    async def test_successfully_get_all_posts(self, post_service) -> None:
        result = await post_service.get_all_posts()
        assert len(result) == 1
        assert self.post == result[0].dict()

    async def test_successfully_get_post_by_uuid(self, post_service) -> None:
        result = await post_service.get_post(self.post['id'])
        assert self.post == result.dict()

    async def test_fail_to_get_post_by_uuid(self, post_service) -> None:
        result = await post_service.get_post(str(uuid.uuid4()))
        assert result is None

    async def test_successfully_update_post(self, config, dynamodb_client, post_service, table) -> None:
        await post_service.update_post(self.post['id'], {'content': 'Updated content'})
        response = table.query(
            KeyConditionExpression=Key('id').eq(self.post['id']),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        assert response['Count'] == 1
        item = response['Items'][0]
        assert 'Updated content' == item['content']
        assert item['updated_at'] is not None
