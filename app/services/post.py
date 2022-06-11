import hashlib
import logging
import uuid
import time
from typing import List

import boto3
from boto3.dynamodb.conditions import Key, Attr
from fastapi import HTTPException
from starlette import status

from app.models.post import Post, Meta
from app.config import Configuration


class PostService:
    logger = logging.getLogger(__name__)
    config = Configuration()
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(f'{config.app_stage}-posts')

    def _generate_slug(self, title: str) -> str:
        return hashlib.sha1(title.encode('utf-8')).hexdigest()[:10]

    def _get_all_posts(self) -> List:
        response = self.table.scan(FilterExpression=Attr('deleted_at').eq(None))
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('deleted_at').eq(None)
            )
            data.extend(response['Items'])
        return data

    def create_post(self, data: dict) -> Post:
        post_meta = Meta(reading_time=60)
        post = Post(id=str(uuid.uuid4()), author=data['author'], title=data['title'], content=data['content'],
                    published_at=data['published_at'], slug=self._generate_slug(str(round(time.time() * 1000))),
                    meta=post_meta)
        self.table.put_item(Item=post.dict())
        self.logger.info(f'Post successfully created post={post}')
        return post

    def delete_post(self, uuid: str):
        post = self.get_post_by_uuid(uuid)
        self.logger.info(f'Post successfully deleted uuid={uuid}')

    def update_post_by_uuid(self, uuid: str, data: dict):
        post = self.get_post_by_uuid(uuid)
        self.logger.info(f'Post successfully updated post={post}')

    def get_all_posts(self) -> List[Post]:
        posts = []
        for post in self._get_all_posts():
            posts.append(Post.parse_obj(post))
        return posts

    def get_post_by_uuid(self, uuid: str) -> Post:
        post = self.table.query(
            KeyConditionExpression=Key('id').eq(uuid),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        if post['Count'] == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'The requested post was not found with id {uuid}')
        return Post.parse_obj(post['Items'][0])
