import uuid

import pendulum
import pytest
from app.models.post import Post
from boto3.dynamodb.conditions import Key, Attr

from app.services.post import PostService


@pytest.mark.asyncio
class TestPostService:
    @pytest.fixture
    def dynamodb_table(self, settings, dynamodb_resource):
        return dynamodb_resource.Table(f'{settings.app_stage}-posts')

    @pytest.fixture
    def post_dict(self) -> dict:
        tags = ['list', 'of', 'keywords']
        title = 'Some random title'
        return {
            'author': 'root',
            'title': title,
            'content': 'Some random content',
            'published_at': pendulum.now().to_iso8601_string(),
            'tags': tags,
            'meta': {
                'description': 'Meta description',
                'language': 'en',
                'keywords': tags,
                'title': title
            }}

    @pytest.fixture
    def post_model(self, post_dict: dict) -> Post:
        post_uuid = str(uuid.uuid4())
        return Post.parse_obj({
            'id': post_uuid,
            'author': post_dict['author'],
            'content': post_dict['content'],
            'created_at': pendulum.now().to_iso8601_string(),
            'deleted_at': None,
            'published_at': post_dict['published_at'],
            'slug': f'some-random-title-{post_uuid}',
            'tags': post_dict['tags'],
            'title': post_dict['title'],
            'updated_at': None,
            'meta': post_dict['meta']})

    @pytest.fixture
    def post_service(self) -> PostService:
        return PostService()

    @pytest.fixture(autouse=True)
    def setup_table(
            self,
            settings,
            dynamodb_resource,
            dynamodb_table,
            post_model: Post):
        table_name = f'{settings.app_stage}-posts'
        dynamodb_resource.create_table(TableName=table_name,
                                       KeySchema=[{'AttributeName': 'id',
                                                   'KeyType': 'HASH'}],
                                       AttributeDefinitions=[{'AttributeName': 'id',
                                                              'AttributeType': 'S'}],
                                       ProvisionedThroughput={'ReadCapacityUnits': 1,
                                                              'WriteCapacityUnits': 1})
        dynamodb_table.put_item(Item=post_model.dict())

    async def test_successfully_create_post(self, post_dict: dict, post_service: PostService) -> None:
        result = await post_service.create_post(post_dict)
        assert post_dict.items() <= result.dict().items()

    async def test_successfully_delete_post(self, dynamodb_table, post_service, post_model):
        await post_service.delete_post(post_model.id)
        response = dynamodb_table.query(
            KeyConditionExpression=Key('id').eq(post_model.id),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        assert response['Count'] == 0

    async def test_successfully_get_all_posts(self, post_service, post_model) -> None:
        result = await post_service.get_all_posts()
        assert len(result) == 1
        assert post_model == result[0]

    async def test_successfully_get_post_by_uuid(self, post_service, post_model) -> None:
        result = await post_service.get_post(post_model.id)
        assert post_model == result

    async def test_fail_to_get_post_by_uuid(self, post_service) -> None:
        result = await post_service.get_post(str(uuid.uuid4()))
        assert result is None

    async def test_successfully_update_post(self, dynamodb_table, post_service, post_model) -> None:
        await post_service.update_post(post_model.id, {'content': 'Updated content'})
        response = dynamodb_table.query(
            KeyConditionExpression=Key('id').eq(post_model.id),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        assert response['Count'] == 1
        item = response['Items'][0]
        assert 'Updated content' == item['content']
        assert item['updated_at'] is not None
