from decimal import Decimal
from typing import Any

import boto3


class RateLimitRepository:
    def __init__(
        self,
        table_name: str,
        db: boto3.resource,
    ):
        self._table = db.Table(table_name)

    def get_rate_limit(self, client_id: str, endpoint: str) -> dict[str, Any] | None:
        response = self._table.get_item(
            Key={
                "client_id": client_id,
                "endpoint": endpoint,
            }
        )
        return response.get("Item")

    def create_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        request_count: int,
        window_start: Decimal,
        ttl: Decimal,
    ) -> None:
        self._table.put_item(
            Item={
                "client_id": client_id,
                "endpoint": endpoint,
                "request_count": request_count,
                "window_start": window_start,
                "ttl": ttl,
            }
        )

    def reset_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        request_count: int,
        window_start: Decimal,
        ttl: Decimal,
    ) -> None:
        self._table.update_item(
            Key={"client_id": client_id, "endpoint": endpoint},
            UpdateExpression=(
                "SET request_count = :val, window_start = :now, #ttl_attr = :ttl"
            ),
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":val": request_count,
                ":now": window_start,
                ":ttl": ttl,
            },
        )

    def increment_rate_limit(self, client_id: str, endpoint: str) -> None:
        self._table.update_item(
            Key={"client_id": client_id, "endpoint": endpoint},
            UpdateExpression="ADD request_count :inc",
            ExpressionAttributeValues={":inc": 1},
        )
