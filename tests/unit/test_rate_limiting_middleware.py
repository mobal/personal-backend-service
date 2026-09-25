import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from app.middlewares import RateLimitingMiddleware
from app.services.rate_limiter_service import RateLimitResult


def make_request(
    path: str, route_template: str | None = None, client_ip: str = "192.0.2.1"
) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": (client_ip, 1234),
        "server": ("testserver", 80),
    }
    if route_template is not None:
        scope["route"] = SimpleNamespace(path=route_template)
    return Request(scope)


class TestRateLimitingMiddleware:
    def test_uses_route_template_instead_of_raw_path(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.middlewares.settings.rate_limiting", True)
        rate_limiter = Mock()
        rate_limiter.check_rate_limit.return_value = RateLimitResult(
            allowed=True,
            request_count=1,
            limit=60,
            remaining=59,
            reset_at=123,
        )
        middleware = RateLimitingMiddleware(FastAPI(), rate_limiter)
        call_next = AsyncMock(return_value=Response())
        request = make_request(
            "/api/v1/posts/550e8400-e29b-41d4-a716-446655440000",
            "/api/v1/posts/{uuid}",
        )

        asyncio.run(middleware.dispatch(request, call_next))

        rate_limiter.check_rate_limit.assert_called_once_with(
            "192.0.2.1", "/api/v1/posts/{uuid}"
        )

    def test_maps_unmatched_paths_to_one_bucket(self, monkeypatch):
        monkeypatch.setattr("app.middlewares.settings.rate_limiting", True)
        rate_limiter = Mock()
        rate_limiter.check_rate_limit.return_value = RateLimitResult(
            allowed=True,
            request_count=1,
            limit=60,
            remaining=59,
            reset_at=123,
        )
        middleware = RateLimitingMiddleware(FastAPI(), rate_limiter)
        call_next = AsyncMock(return_value=Response())

        for path in ("/nonsense/one", "/another/random/path"):
            asyncio.run(middleware.dispatch(make_request(path), call_next))

        assert [
            call.args[1] for call in rate_limiter.check_rate_limit.call_args_list
        ] == [
            "unmatched",
            "unmatched",
        ]

    def test_health_endpoint_skips_application_rate_limiting(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.middlewares.settings.rate_limiting", True)
        rate_limiter = Mock()
        middleware = RateLimitingMiddleware(FastAPI(), rate_limiter)
        response = Response()
        call_next = AsyncMock(return_value=response)

        result = asyncio.run(
            middleware.dispatch(make_request("/health", "/health"), call_next)
        )

        assert result is response
        rate_limiter.check_rate_limit.assert_not_called()
