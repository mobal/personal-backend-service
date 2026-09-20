from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from aws_lambda_powertools import Logger

from app.repositories.rate_limit_repository import RateLimitRepository
from app.settings import Settings


@dataclass
class RateLimitResult:
    allowed: bool
    request_count: int
    limit: int
    remaining: int
    reset_at: int


class RateLimiterService:
    def __init__(
        self,
        settings: Settings,
        rate_limit_repository: RateLimitRepository,
    ):
        self._settings = settings
        self._logger = Logger()
        self._rate_limit_repository = rate_limit_repository
        self._max_requests = self._settings.rate_limit_requests
        self._window_duration = self._settings.rate_limit_duration_in_seconds

    def check_rate_limit(self, client_id: str, endpoint: str) -> RateLimitResult:
        now = datetime.now(UTC).timestamp()
        now_dec = Decimal(str(now))
        window_end = now + self._window_duration
        ttl_dec = Decimal(str(int(window_end)))

        item = self._rate_limit_repository.get_rate_limit(client_id, endpoint)

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
        self._rate_limit_repository.create_rate_limit(
            client_id,
            endpoint,
            request_count=1,
            window_start=now,
            ttl=ttl,
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
        self._rate_limit_repository.reset_rate_limit(
            client_id,
            endpoint,
            request_count=1,
            window_start=now,
            ttl=ttl,
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
        self._rate_limit_repository.increment_rate_limit(client_id, endpoint)
        new_count = item["request_count"] + 1
        window_start = Decimal(str(item["window_start"]))
        return RateLimitResult(
            allowed=True,
            request_count=new_count,
            limit=self._max_requests,
            remaining=self._max_requests - new_count,
            reset_at=int(window_start + Decimal(str(self._window_duration))),
        )
