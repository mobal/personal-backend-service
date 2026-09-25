import pytest
from fastapi.testclient import TestClient

from app.api_handler import app
from app.middlewares import RateLimitingMiddleware


class TestHealthApi:
    def test_health_does_not_call_application_dependencies(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        if app.middleware_stack is None:
            app.middleware_stack = app.build_middleware_stack()
        middleware = app.middleware_stack
        while not isinstance(middleware, RateLimitingMiddleware):
            middleware = middleware.app

        def fail_if_called(*args, **kwargs):
            raise AssertionError(
                "Health check must not access application dependencies"
            )

        monkeypatch.setattr(
            middleware._rate_limiter, "check_rate_limit", fail_if_called
        )
        monkeypatch.setattr("app.settings.parameters.get_parameter", fail_if_called)

        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
