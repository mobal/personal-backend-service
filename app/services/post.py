import logging
import uuid
from typing import List, Optional

import boto3
import pendulum
from aws_lambda_powertools import Tracer
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException
from slugify import slugify
from starlette import status

from app.settings import Settings
from app.models.post import Post


tracer = Tracer()


def create_slug(title: str, post_uuid: str) -> str:
    return f'{slugify(title)}-{post_uuid}'


class PostService:
    def __init__(self):
        self._logger = logging.getLogger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self.table = dynamodb.Table(f'{settings.app_stage}-posts')

    @tracer.capture_method
    async def _delete_post_by_uuid(self, post_uuid: str):
        post = await self._get_post_by_uuid(post_uuid)
        post.deleted_at = pendulum.now().to_iso8601_string()
        self.table.put_item(Item=post.dict())

    @tracer.capture_method
    async def _get_all_posts(self) -> List:
        response = self.table.scan(FilterExpression=Attr('deleted_at').eq(None))
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('deleted_at').eq(None),
            )
            data.extend(response['Items'])
        return data

    @tracer.capture_method
    async def _get_post_by_uuid(self, post_uuid: str) -> Optional[Post]:
        response = self.table.query(
            KeyConditionExpression=Key('id').eq(post_uuid),
            FilterExpression=Attr('deleted_at').eq(None),
        )
        if response['Count'] != 0:
            return Post.parse_obj(response['Items'][0])
        error_message = f'The requested post was not found with id {post_uuid}'
        raise HTTPException(status.HTTP_404_NOT_FOUND, error_message)

    @tracer.capture_method
    async def create_post(self, data: dict) -> Post:
        post_uuid = str(uuid.uuid4())
        post = Post(
            id=post_uuid,
            author=data['author'],
            title=data['title'],
            content=data['content'],
            created_at=pendulum.now().to_iso8601_string(),
            published_at=data['published_at'],
            slug=create_slug(data['title'], post_uuid),
            tags=data['tags'],
            meta=data['meta'],
        )
        self.table.put_item(Item=post.dict())
        self._logger.info(f'Post successfully created {post=}')
        return post

    @tracer.capture_method
    async def delete_post(self, post_uuid: str):
        await self._delete_post_by_uuid(post_uuid)
        self._logger.info(f'Post successfully deleted {post_uuid=}')

    @tracer.capture_method
    async def get_all_posts(self) -> List[Post]:
        posts = []
        for post in await self._get_all_posts():
            posts.append(Post.parse_obj(post))
        return posts

    @tracer.capture_method
    async def get_post(self, post_uuid: str) -> Optional[Post]:
        return await self._get_post_by_uuid(post_uuid)

    @tracer.capture_method
    async def update_post(self, post_uuid: str, data: dict) -> None:
        post = await self._get_post_by_uuid(post_uuid)
        post = post.copy(update=data)
        post.updated_at = pendulum.now().to_iso8601_string()
        self.table.put_item(Item=post.dict())
        self._logger.info(f'Post successfully updated {post=}')
