from typing import Any

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import AttributeBase, Key

from app.settings import Settings


class PostRepository:
    SELECT_COUNT = "COUNT"

    def __init__(self):
        self._logger = Logger(utc=True)
        settings = Settings()
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-posts")
        )

    async def create_post(self, data: dict):
        self._table.put_item(Item=data)

    async def get_all_posts(
        self, filter_expression: AttributeBase, fields: list[str] = None
    ) -> list[dict[str, Any]]:
        projection_expression = ",".join(fields)
        response = self._table.scan(
            FilterExpression=filter_expression,
            ProjectionExpression=projection_expression,
        )
        items = response["Items"]
        while "LastEvaluatedKey" in response:
            response = self._table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"],
                FilterExpression=filter_expression,
                ProjectionExpression=projection_expression,
            )
            items.extend(response["Items"])
        return items

    async def count_all_posts(self, filter_expression: AttributeBase) -> int:
        response = self._table.scan(
            Select=PostRepository.SELECT_COUNT,
            FilterExpression=filter_expression,
        )
        return response["Count"]

    async def item_count(self) -> int:
        return self._table.item_count

    async def get_post_by_post_path(
        self, post_path: str, filter_expression: AttributeBase
    ) -> dict | None:
        response = self._table.query(
            IndexName="PostPathIndex",
            KeyConditionExpression=Key("post_path").eq(post_path),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    async def get_post_by_title(
        self, title: str, filter_expression: AttributeBase
    ) -> dict | None:
        response = self._table.query(
            IndexName="TitleIndex",
            KeyConditionExpression=Key("title").eq(title),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    async def get_post_by_uuid(
        self,
        post_uuid: str,
        filter_expression: AttributeBase,
    ) -> dict | None:
        response = self._table.query(
            KeyConditionExpression=Key("id").eq(post_uuid),
            FilterExpression=filter_expression,
        )
        if response["Items"]:
            return response["Items"][0]
        return None

    async def get_posts(
        self,
        filter_expression: AttributeBase,
        exclusive_start_key: str | None,
        fields: list[str] = None,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        kwargs = {
            "FilterExpression": filter_expression,
            "ProjectionExpression": ",".join(fields),
        }
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key
        response = self._table.scan(**kwargs)
        return response.get("LastEvaluatedKey"), response["Items"]

    async def update_post(
        self, post_uuid: str, data: dict, condition_expression: AttributeBase
    ):
        attribute_names = {}
        attribute_values = {}
        update_expression = []
        for k, v in data.items():
            attribute_names[f"#{k}"] = k
            attribute_values[f":{k}"] = v
            update_expression.append(f"#{k}=:{k}")
        self._table.update_item(
            Key={"id": post_uuid},
            ConditionExpression=condition_expression,
            UpdateExpression="SET " + ",".join(update_expression),
            ExpressionAttributeNames=attribute_names,
            ExpressionAttributeValues=attribute_values,
        )
