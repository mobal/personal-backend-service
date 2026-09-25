from dataclasses import dataclass
from datetime import UTC, datetime

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
        now = int(datetime.now(UTC).timestamp())
        window_start = now // self._window_duration * self._window_duration
        reset_at = window_start + self._window_duration
        bucket_key = f"{endpoint}#{window_start}"
        ttl = reset_at + self._window_duration

        request_count = self._rate_limit_repository.consume_request(
            client_id=client_id,
            endpoint=bucket_key,
            limit=self._max_requests,
            window_start=window_start,
            ttl=ttl,
        )
        if request_count is None:
            self._logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "max_requests": self._max_requests,
                },
            )
            return RateLimitResult(
                allowed=False,
                request_count=self._max_requests,
                limit=self._max_requests,
                remaining=0,
                reset_at=reset_at,
            )

        return RateLimitResult(
            allowed=True,
            request_count=request_count,
            limit=self._max_requests,
            remaining=self._max_requests - request_count,
            reset_at=reset_at,
        )
