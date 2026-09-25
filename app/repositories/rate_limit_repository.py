from typing import Any

import boto3
from botocore.exceptions import ClientError


class RateLimitRepository:
    def __init__(
        self,
        table_name: str,
        db: boto3.resource,
    ):
        self._table = db.Table(table_name)

    def consume_request(
        self,
        client_id: str,
        endpoint: str,
        limit: int,
        window_start: int,
        ttl: int,
    ) -> int | None:
        try:
            response: dict[str, Any] = self._table.update_item(
                Key={"client_id": client_id, "endpoint": endpoint},
                UpdateExpression=(
                    "SET window_start = :window_start, #ttl = :ttl "
                    "ADD request_count :one"
                ),
                ConditionExpression=(
                    "attribute_not_exists(request_count) OR request_count < :limit"
                ),
                ExpressionAttributeNames={"#ttl": "ttl"},
                ExpressionAttributeValues={
                    ":window_start": window_start,
                    ":ttl": ttl,
                    ":one": 1,
                    ":limit": limit,
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise

        return int(response["Attributes"]["request_count"])
