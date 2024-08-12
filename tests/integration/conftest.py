import uuid

import pendulum
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from respx import MockRouter, Route

from app.main import app
from app.models.auth import Role
from tests.helpers.utils import generate_jwt_token


@pytest.fixture
async def cache_service_mock_200(respx_mock: MockRouter) -> Route:
    jwt_token, token_id = await generate_jwt_token(
        [Role.POST_CREATE, Role.POST_DELETE, Role.POST_UPDATE],
        pytest.jwt_secret_ssm_param_value,
    )
    return respx_mock.route(
        method="GET", url__startswith=pytest.cache_service_base_url
    ).mock(
        Response(
            status_code=status.HTTP_200_OK,
            json={
                "key": f"jti_{token_id}",
                "value": jwt_token,
                "createdAt": pendulum.now().to_iso8601_string(),
            },
        )
    )


@pytest.fixture
def cache_service_mock_404(respx_mock: MockRouter) -> Route:
    return respx_mock.route(
        headers={}, method="GET", url__startswith=pytest.cache_service_base_url
    ).mock(
        Response(
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                "status": status.HTTP_404_NOT_FOUND,
                "id": str(uuid.uuid4()),
                "message": "Not found",
            },
        )
    )


@pytest.fixture
def cache_service_mock_500(respx_mock: MockRouter) -> Route:
    return respx_mock.route(
        headers={}, method="GET", url__startswith=pytest.cache_service_base_url
    ).mock(
        Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            json={
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "id": str(uuid.uuid4()),
                "message": "Not found",
            },
        )
    )


@pytest.fixture
def test_client(initialize_posts_table) -> TestClient:
    return TestClient(app, raise_server_exceptions=True)
