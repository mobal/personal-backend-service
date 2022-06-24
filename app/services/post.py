import encodings.utf_8
import hashlib
import logging
import uuid
from typing import List, Optional

import boto3
import pendulum
from boto3.dynamodb.conditions import Key, Attr
from slugify import slugify

from app.models.post import Post
from app.config import Configuration


def create_slug(title: str) -> str:
    return f'{slugify(title)}-{hashlib.sha1(title.encode(encodings.utf_8.getregentry().name)).hexdigest()[:10]}'


class PostService:
    def __init__(self) -> None:
        self.logger = logging.getLogger()
        config = Configuration()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self.table = dynamodb.Table(f'{config.app_stage}-posts')

    async def _delete_post_by_uuid(self, uuid: str) -> None:
        post = await self._get_post_by_uuid(uuid)
        post.deleted_at = pendulum.now().to_iso8601_string()
        self.table.put_item(Item=post.dict())

    async def _get_all_posts(self) -> List:
        response = self.table.scan(FilterExpression=Attr('deleted_at').eq(None))
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('deleted_at').eq(None)
            )
            data.extend(response['Items'])
        return data

    async def _get_post_by_uuid(self, uuid: str) -> Optional[Post]:
        response = self.table.query(
            KeyConditionExpression=Key('id').eq(uuid),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        return Post.parse_obj(response['Items'][0]) if response['Count'] != 0 else None

    async def create_post(self, data: dict) -> Post:
        post = Post(id=str(uuid.uuid4()), author=data['author'], title=data['title'], content=data['content'],
                    created_at=pendulum.now().to_iso8601_string(), published_at=data['published_at'],
                    slug=create_slug(data['title']))
        self.table.put_item(Item=post.dict())
        self.logger.info(f'Post successfully created post={post}')
        return post

    async def delete_post(self, uuid: str) -> None:
        await self._delete_post_by_uuid(uuid)
        self.logger.info(f'Post successfully deleted uuid={uuid}')

    async def get_all_posts(self) -> List[Post]:
        posts = []
        for post in await self._get_all_posts():
            posts.append(Post.parse_obj(post))
        return posts

    async def get_post(self, uuid: str) -> Optional[Post]:
        return await self._get_post_by_uuid(uuid)

    async def update_post(self, uuid: str, data: dict) -> None:
        post = await self._get_post_by_uuid(uuid)
        post = post.copy(update=data)
        post.updated_at = pendulum.now().to_iso8601_string()
        self.table.put_item(Item=post.dict())
        self.logger.info(f'Post successfully updated post={post}')
