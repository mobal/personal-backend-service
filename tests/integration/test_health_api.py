import pytest
from fastapi.testclient import TestClient


class TestHealthApi:
    def test_health_does_not_call_application_dependencies(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        def fail_if_called(*args, **kwargs):
            raise AssertionError(
                "Health check must not access application dependencies"
            )

        monkeypatch.setattr("app.settings.parameters.get_parameter", fail_if_called)

        response = test_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_unknown_route_returns_the_standard_error_shape(
        self, test_client: TestClient
    ):
        response = test_client.get("/does-not-exist")

        assert response.status_code == 404
        body = response.json()
        assert body["status"] == 404
        assert body["message"] == "Not Found"
        assert body["id"]
        assert response.headers["X-Correlation-ID"]
