from typing import List, Optional

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key, AttributeBase

from app.exceptions import PostNotFoundException
from app.settings import Settings


class PostRepository:
    def __init__(self):
        self._logger = Logger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self._table = dynamodb.Table(f'{settings.app_stage}-posts')

    async def create_post(self, data: dict):
        self._table.put_item(Item=data)

    async def get_all_posts(
        self, filter_expression: AttributeBase, fields: Optional[str] = None
    ) -> List[dict]:
        kwargs = {'FilterExpression': filter_expression}
        if fields:
            kwargs['ProjectionExpression'] = fields
        response = self._table.scan(**kwargs)
        items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self._table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                **kwargs,
            )
            items.extend(response['Items'])
        return items

    async def get_post_by_uuid(
        self,
        post_uuid: str,
        filter_expression: AttributeBase,
    ) -> dict:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(post_uuid),
            FilterExpression=filter_expression,
        )
        if response['Count'] == 1:
            return response['Items'][0]
        raise PostNotFoundException(f'Post was not found with UUID {post_uuid=}')

    async def update_post(
        self, post_uuid: str, data: dict, filter_expression: AttributeBase
    ):
        item = await self.get_post_by_uuid(post_uuid, filter_expression)
        item.update(data)
        self._table.put_item(Item=item)
