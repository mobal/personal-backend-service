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
