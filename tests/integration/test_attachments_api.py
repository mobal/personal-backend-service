import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from mypy_boto3_cloudformation import ServiceResource
from respx import MockRouter

from app.middlewares import COUNTRY_IS_API_BASE_URL, banned_hosts
from app.models.post import Attachment, Post
from app.schemas.attachment_schema import CreateAttachment
from tests.helpers.utils import generate_jwt_token


class TestAttachmentsApi:
    @pytest.fixture
    def create_attachment(self, test_data: str) -> CreateAttachment:
        return CreateAttachment(
            name="lorem.txt",
            data=test_data,
        )

    @pytest.fixture(autouse=True)
    def setup_function(self, s3_resource: ServiceResource, respx_mock: MockRouter):
        s3_resource.create_bucket(
            ACL="public-read-write",
            Bucket="attachments",
            CreateBucketConfiguration={"LocationConstraint": pytest.aws_default_region},
        )
        banned_hosts.clear()
        respx_mock.route(method="GET", url__startswith=COUNTRY_IS_API_BASE_URL).mock(
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "8.8.8.8",
                    "country": "US",
                },
            ),
        )

    def test_successfully_add_attachment(
        self,
        attachment: Attachment,
        create_attachment: CreateAttachment,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{posts[0].id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]

    def test_fail_to_add_attachment_due_to_bad_request(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{post_with_attachment.id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert result["id"]
        assert result["message"]
        assert result["errors"]

    def test_fail_to_add_attachment_due_to_unauthorized(
        self,
        create_attachment: CreateAttachment,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(pytest.jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{post_with_attachment.id}/attachments",
            headers={"Authorization": "Bearer "},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert {
            "status": status.HTTP_403_FORBIDDEN,
            "message": "Not authenticated",
        }.items() <= response.json().items()

    def test_successfully_get_attachment_by_uuid(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{post_with_attachment.attachments[0].id}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json().items()
            <= post_with_attachment.attachments[0].model_dump(by_alias=True).items()
        )

    def test_fail_to_get_attachment_due_to_invalid_client(
        self,
        respx_mock: MockRouter,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        route_mock = respx_mock.route(
            method="GET",
            url__startswith=COUNTRY_IS_API_BASE_URL,
        ).mock(
            Response(
                status_code=status.HTTP_200_OK,
                json={
                    "ip": "testclient",
                    "country": "RU",
                },
            ),
        )

        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{post_with_attachment.attachments[0].id}"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"message": "Forbidden"}
        assert route_mock.called
        assert route_mock.call_count == 1

    def test_fail_to_get_attachment_due_to_not_found(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{str(uuid.uuid4())}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()

    def test_successfully_get_attachments(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments"
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.json()[0].items()
            <= post_with_attachment.model_dump(include=["attachments"], by_alias=True)[
                "attachments"
            ][0].items()
        )

    def test_successfully_get_empty_attachments(
        self,
        posts: list[Post],
        test_client: TestClient,
    ):
        response = test_client.get(f"/api/v1/posts/{posts[0].id}/attachments")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
