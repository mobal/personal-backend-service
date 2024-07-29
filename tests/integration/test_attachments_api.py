import uuid

import pendulum
import pytest
from fastapi import status
from httpx import Response
from mypy_boto3_cloudformation import ServiceResource
from respx import MockRouter, Route
from starlette.testclient import TestClient

from app.middlewares import COUNTRY_IS_API_BASE_URL, banned_hosts
from app.models.post import Attachment, Post
from app.schemas.attachment_schema import CreateAttachment
from tests.helpers.utils import generate_jwt_token

CACHE_SERVICE_URL = f"{pytest.cache_service_base_url}/api/cache"
ROLE_ATTACHMENT_CREATE = "attachment:create"


@pytest.mark.asyncio
class TestAttachmentsApi:
    async def __generate_respx_mock(
        self,
        method: str,
        response: Response,
        respx_mock: MockRouter,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> Route:
        return respx_mock.route(
            headers=headers, method=method, url__startswith=url
        ).mock(response)

    @pytest.fixture
    async def cache_service_response_404(self) -> Response:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                "status": status.HTTP_404_NOT_FOUND,
                "id": str(uuid.uuid4()),
                "message": "Not found",
            },
        )

    @pytest.fixture
    def create_attachment(self, test_data: str) -> CreateAttachment:
        return CreateAttachment(
            name="lorem.txt",
            data=test_data,
        )

    @pytest.fixture(autouse=True)
    async def setup_function(
        self, s3_resource: ServiceResource, respx_mock: MockRouter
    ):
        s3_resource.create_bucket(
            ACL="public-read-write",
            Bucket="attachments",
            CreateBucketConfiguration={"LocationConstraint": pytest.aws_default_region},
        )
        banned_hosts.clear()
        await self.__generate_respx_mock(
            "GET",
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "8.8.8.8",
                    "country": "US",
                },
            ),
            respx_mock,
            COUNTRY_IS_API_BASE_URL,
        )

    async def test_successfully_add_attachment(
        self,
        attachment: Attachment,
        cache_service_response_404: Response,
        create_attachment: CreateAttachment,
        posts: list[Post],
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token, _ = await generate_jwt_token(
            [ROLE_ATTACHMENT_CREATE], pytest.jwt_secret
        )
        cache_service_mock = await self.__generate_respx_mock(
            "GET",
            cache_service_response_404,
            respx_mock,
            CACHE_SERVICE_URL,
        )

        response = test_client.post(
            f"/api/v1/posts/{posts[0].id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def test_successfully_get_attachment_by_uuid(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{post_with_attachment.attachments[0].id}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == post_with_attachment.attachments[0].model_dump(
            by_alias=True
        )

    async def test_fail_to_get_attachment_due_to_not_found(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{str(uuid.uuid4())}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()

    async def test_successfully_get_attachments(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments"
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()
            == post_with_attachment.model_dump(include=["attachments"], by_alias=True)[
                "attachments"
            ]
        )

    async def test_successfully_get_empty_attachments(
        self,
        posts: list[Post],
        test_client: TestClient,
    ):
        response = test_client.get(f"/api/v1/posts/{posts[0].id}/attachments")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
