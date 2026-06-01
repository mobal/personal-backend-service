from typing import Any

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import ConditionBase, Key

from app.settings import Settings


class PostRepository:
    def __init__(
        self,
        settings: Settings,
        table_name: str | None = None,
        db_resource: boto3.resource | None = None,
        logger: Logger | None = None,
    ):
        self._settings = settings
        self._logger = logger or Logger()
        db = db_resource or boto3.resource("dynamodb")
        resolved_table = table_name or f"{self._settings.stage}-posts"
        self._table = db.Table(resolved_table)

    def create_post(self, data: dict):
        self._table.put_item(Item=data)

    def get_all_posts(
        self, filter_expression: ConditionBase, fields: list[str]
    ) -> list[dict[str, Any]]:
        items = []
        last_key = None
        while True:
            exclusive_start_key = {"id": last_key} if last_key else None
            last_key, page = self.get_posts(
                filter_expression, exclusive_start_key, fields
            )
            items.extend(page)
            if last_key is None:
                break
        return items

    def count_all_posts(self, filter_expression: ConditionBase) -> int:
        count = 0
        response = self._table.scan(Select="COUNT", FilterExpression=filter_expression)
        count += response["Count"]
        while "LastEvaluatedKey" in response:
            response = self._table.scan(
                Select="COUNT",
                ExclusiveStartKey=response["LastEvaluatedKey"],
                FilterExpression=filter_expression,
            )
            count += response["Count"]
        return count

    def item_count(self) -> int:
        return self._table.item_count

    def get_post_by_post_path(
        self, post_path: str, filter_expression: ConditionBase
    ) -> dict | None:
        response = self._table.query(
            IndexName="PostPathIndex",
            KeyConditionExpression=Key("post_path").eq(post_path),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    def get_post_by_title(
        self, title: str, filter_expression: ConditionBase
    ) -> dict | None:
        response = self._table.query(
            IndexName="TitleIndex",
            KeyConditionExpression=Key("title").eq(title),
            FilterExpression=filter_expression,
        )
        return response["Items"][0] if response["Items"] else None

    def get_post_by_uuid(self, post_uuid: str) -> dict | None:
        response = self._table.get_item(Key={"id": post_uuid})
        return response.get("Item")

    def get_posts(
        self,
        filter_expression: ConditionBase,
        exclusive_start_key: dict[str, str] | None = None,
        fields: list[str] | None = None,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        kwargs = {
            "FilterExpression": filter_expression,
            "ExclusiveStartKey": exclusive_start_key,
            "ProjectionExpression": ",".join(fields) if fields else None,
        }
        response = self._table.scan(
            **{k: v for k, v in kwargs.items() if v is not None}
        )
        last_key = response.get("LastEvaluatedKey", {}).get("id")
        return last_key, response["Items"]

    def update_post(
        self,
        post_uuid: str,
        data: dict,
        condition_expression: ConditionBase,
    ):
        attr_names = {f"#{k}": k for k in data}
        attr_values = {f":{k}": v for k, v in data.items()}
        update_expr = ", ".join(f"#{k}=:{k}" for k in data)
        update_kwargs = {
            "Key": {"id": post_uuid},
            "ConditionExpression": condition_expression,
            "UpdateExpression": f"SET {update_expr}",
            "ExpressionAttributeNames": attr_names,
            "ExpressionAttributeValues": attr_values,
        }

        self._table.update_item(**update_kwargs)
