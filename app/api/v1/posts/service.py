from typing import List

import boto3
from boto3.dynamodb.conditions import Key, Attr

from app.api.v1.posts.models import Post
from app.config import Configuration


class PostService:
    config = Configuration()
    session = boto3.Session()
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(f'{config.app_stage}-posts')

    def _get_all_posts_from_db(self) -> List:
        response = self.table.scan(FilterExpression=Attr('deleted_at').eq(None))
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression=Attr('deleted_at').eq(None)
            )
            data.extend(response['Items'])
        return data

    def get_all_posts(self) -> List[Post]:
        posts = []
        for post in self._get_all_posts_from_db():
            posts.append(Post.parse_obj(post))
        return posts

    def get_post_by_id(self, uuid: str) -> Post:
        post = self.table.query(
            KeyConditionExpression=Key('id').eq(uuid),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        if post['Count'] > 1:
            raise ValueError(f'There is more than one post with this id {uuid}')
        return Post.parse_obj(post['Items'][0])
