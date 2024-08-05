from typing import Any

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import ConditionBase, Key

from app import settings


class PostRepository:
    def __init__(self):
        self.__logger = Logger(utc=True)
        self.__table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-posts")
        )

    async def create_post(self, data: dict):
        self.__table.put_item(Item=data)

    async def get_all_posts(
        self,
        filter_expression: ConditionBase,
        fields: list[str],
    ) -> list[dict[str, Any]]:
        projection_expression = ",".join(fields)
        response = self.__table.scan(
            FilterExpression=filter_expression,
            ProjectionExpression=projection_expression,
        )
        items = response["Items"]
        while "LastEvaluatedKey" in response:
            response = self.__table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"],
                FilterExpression=filter_expression,
                ProjectionExpression=projection_expression,
            )
            items.extend(response["Items"])
        return items

    async def count_all_posts(self, filter_expression: ConditionBase) -> int:
        count = 0
        response = self.__table.scan(
            Select="COUNT",
            FilterExpression=filter_expression,
        )
        count += response["Count"]
        while "LastEvaluatedKey" in response:
            response = self.__table.scan(
                Select="COUNT",
                ExclusiveStartKey=response["LastEvaluatedKey"],
                FilterExpression=filter_expression,
            )
            count += response["Count"]
        return count

    async def item_count(self) -> int:
        return self.__table.item_count

    async def get_post_by_post_path(
        self, post_path: str, filter_expression: ConditionBase
    ) -> dict | None:
        response = self.__table.query(
            IndexName="PostPathIndex",
            KeyConditionExpression=Key("post_path").eq(post_path),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    async def get_post_by_title(
        self, title: str, filter_expression: ConditionBase
    ) -> dict | None:
        response = self.__table.query(
            IndexName="TitleIndex",
            KeyConditionExpression=Key("title").eq(title),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    async def get_post_by_uuid(
        self,
        post_uuid: str,
        filter_expression: ConditionBase,
    ) -> dict | None:
        response = self.__table.query(
            KeyConditionExpression=Key("id").eq(post_uuid),
            FilterExpression=filter_expression,
        )
        if response["Items"]:
            return response["Items"][0]
        return None

    async def get_posts(
        self,
        filter_expression: ConditionBase,
        exclusive_start_key: dict[str, str] | None = None,
        fields: list[str] | None = None,
    ) -> tuple[str | None, list[dict[str, Any]]]:

        kwargs: dict[str, Any] = {}
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key
        if fields:
            kwargs["ProjectionExpression"] = ",".join(fields)
        kwargs["FilterExpression"] = filter_expression
        response = self.__table.scan(**kwargs)
        return (
            response["LastEvaluatedKey"]["id"]
            if response.get("LastEvaluatedKey", None)
            else None
        ), response["Items"]

    async def update_post(
        self, post_uuid: str, data: dict, condition_expression: ConditionBase
    ):
        attribute_names = {}
        attribute_values = {}
        update_expression = []
        for k, v in data.items():
            attribute_names[f"#{k}"] = k
            attribute_values[f":{k}"] = v
            update_expression.append(f"#{k}=:{k}")
        self.__table.update_item(
            Key={"id": post_uuid},
            ConditionExpression=condition_expression,
            UpdateExpression="SET " + ",".join(update_expression),
            ExpressionAttributeNames=attribute_names,
            ExpressionAttributeValues=attribute_values,
        )
