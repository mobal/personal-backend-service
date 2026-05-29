from dataclasses import dataclass
from decimal import Decimal

import boto3
import pendulum
from aws_lambda_powertools import Logger

from app import settings


@dataclass
class RateLimitResult:
    allowed: bool
    request_count: int
    limit: int
    remaining: int
    reset_at: int


class RateLimiterService:
    def __init__(self, stage: str | None = None):
        self._logger = Logger()
        self._stage = stage or settings.stage
        self._table = boto3.resource("dynamodb").Table(f"{self._stage}-rate-limits")
        self._max_requests = settings.rate_limit_requests
        self._window_duration = settings.rate_limit_duration_in_seconds

    def check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitResult:
        now = pendulum.now().timestamp()
        now_dec = Decimal(str(now))
        window_end = now + self._window_duration
        ttl_dec = Decimal(str(int(window_end)))

        response = self._table.get_item(
            Key={
                "client_id": client_id,
                "endpoint": endpoint,
            }
        )
        item = response.get("Item")

        if not item:
            return self._create_new_record(
                client_id, endpoint, now_dec, ttl_dec, window_end
            )

        window_start = Decimal(str(item["window_start"]))
        if window_start + Decimal(str(self._window_duration)) < now_dec:
            return self._reset_window(client_id, endpoint, now_dec, ttl_dec, window_end)

        if item["request_count"] >= self._max_requests:
            return self._rate_limited(item)

        return self._increment_counter(client_id, endpoint, item)

    def _create_new_record(
        self,
        client_id: str,
        endpoint: str,
        now: Decimal,
        ttl: Decimal,
        window_end: float,
    ) -> RateLimitResult:
        self._table.put_item(
            Item={
                "client_id": client_id,
                "endpoint": endpoint,
                "request_count": 1,
                "window_start": now,
                "ttl": ttl,
            }
        )
        return RateLimitResult(
            allowed=True,
            request_count=1,
            limit=self._max_requests,
            remaining=self._max_requests - 1,
            reset_at=int(window_end),
        )

    def _reset_window(
        self,
        client_id: str,
        endpoint: str,
        now: Decimal,
        ttl: Decimal,
        window_end: float,
    ) -> RateLimitResult:
        self._table.update_item(
            Key={"client_id": client_id, "endpoint": endpoint},
            UpdateExpression=(
                "SET request_count = :val, window_start = :now, #ttl_attr = :ttl"
            ),
            ExpressionAttributeNames={"#ttl_attr": "ttl"},
            ExpressionAttributeValues={
                ":val": 1,
                ":now": now,
                ":ttl": ttl,
            },
        )
        return RateLimitResult(
            allowed=True,
            request_count=1,
            limit=self._max_requests,
            remaining=self._max_requests - 1,
            reset_at=int(window_end),
        )

    def _rate_limited(self, item: dict) -> RateLimitResult:
        self._logger.warning(
            "Rate limit exceeded",
            extra={
                "client_id": item.get("client_id"),
                "endpoint": item.get("endpoint"),
                "request_count": item["request_count"],
                "max_requests": self._max_requests,
            },
        )
        return RateLimitResult(
            allowed=False,
            request_count=item["request_count"],
            limit=self._max_requests,
            remaining=0,
            reset_at=int(
                Decimal(str(item["window_start"])) + Decimal(str(self._window_duration))
            ),
        )

    def _increment_counter(
        self, client_id: str, endpoint: str, item: dict
    ) -> RateLimitResult:
        self._table.update_item(
            Key={"client_id": client_id, "endpoint": endpoint},
            UpdateExpression="ADD request_count :inc",
            ExpressionAttributeValues={":inc": 1},
        )
        new_count = item["request_count"] + 1
        window_start = Decimal(str(item["window_start"]))
        return RateLimitResult(
            allowed=True,
            request_count=new_count,
            limit=self._max_requests,
            remaining=self._max_requests - new_count,
            reset_at=int(window_start + Decimal(str(self._window_duration))),
        )
