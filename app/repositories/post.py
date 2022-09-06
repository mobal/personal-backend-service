from typing import List, Optional

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key, AttributeBase

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
        self, filter_expression: AttributeBase, fields: Optional[List[str]] = None
    ) -> List[dict]:
        kwargs = {'FilterExpression': filter_expression}
        if fields:
            kwargs['ProjectionExpression'] = ','.join(fields)
        response = self._table.scan(**kwargs)
        items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self._table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                **kwargs,
            )
            items.extend(response['Items'])
        return items

    async def get_post(self, filter_expression: AttributeBase) -> Optional[dict]:
        response = self._table.scan(FilterExpression=filter_expression)
        if response['Items']:
            return response['Items'][0]
        return None

    async def get_post_by_uuid(
        self,
        post_uuid: str,
        filter_expression: AttributeBase,
    ) -> Optional[dict]:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(post_uuid),
            FilterExpression=filter_expression,
        )
        if response['Items']:
            return response['Items'][0]
        return None

    async def update_post(
        self, post_uuid: str, data: dict, condition_expression: AttributeBase
    ):
        attribute_names = {}
        attribute_values = {}
        update_expression = []
        for k, v in data.items():
            attribute_names[f'#{k}'] = k
            attribute_values[f':{k}'] = str(v)
            update_expression.append(f'#{k}=:{k}')
        self._table.update_item(
            Key={'id': post_uuid},
            ConditionExpression=condition_expression,
            UpdateExpression='SET ' + ','.join(update_expression),
            ExpressionAttributeNames=attribute_names,
            ExpressionAttributeValues=attribute_values,
        )
