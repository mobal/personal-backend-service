import uuid
from typing import List

import boto3
import pendulum
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key, AttributeBase

from app.exception import PostNotFoundException
from app.models.post import Post
from app.settings import Settings


class PostRepository:
    def __init__(self):
        self._logger = Logger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self._table = dynamodb.Table(f'{settings.app_stage}-posts')

    async def create_post(self, data: dict) -> Post:
        post_uuid = str(uuid.uuid4())
        post = Post(
            id=post_uuid,
            author=data['author'],
            title=data['title'],
            content=data['content'],
            created_at=pendulum.now().to_iso8601_string(),
            published_at=data['published_at'],
            slug=data['slug'],
            tags=data['tags'],
            meta=data['meta'],
        )
        self._table.put_item(Item=post.dict())
        return post

    async def delete_post(self, post_uuid: str, filter_expression: AttributeBase):
        post = await self.get_post_by_uuid(post_uuid, filter_expression)
        if post.deleted_at is None:
            post.deleted_at = pendulum.now().to_iso8601_string()
            self._table.put_item(Item=post.dict())

    async def get_all_posts(self, filter_expression: AttributeBase) -> List[Post]:
        posts = []
        response = self._table.scan(FilterExpression=filter_expression)
        items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self._table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=filter_expression,
            )
            items.extend(response['Items'])

        for item in items:
            posts.append(Post.parse_obj(item))
        return posts

    async def get_post_by_uuid(
        self,
        post_uuid: str,
        filter_expression: AttributeBase,
    ) -> Post:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(post_uuid),
            FilterExpression=filter_expression,
        )
        if response['Count'] == 1:
            return Post.parse_obj(response['Items'][0])
        raise PostNotFoundException(f'Post was not found with UUID {post_uuid=}')

    async def update_post(
        self, post_uuid: str, data: dict, filter_expression: AttributeBase
    ):
        post = await self.get_post_by_uuid(post_uuid, filter_expression)
        post = post.copy(update=data)
        post.updated_at = pendulum.now().to_iso8601_string()
        self._table.put_item(Item=post.dict())
