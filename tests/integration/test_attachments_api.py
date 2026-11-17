import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from tests.helpers.utils import generate_jwt_token

from app.models.post import Attachment, Post
from app.schemas.attachment_schema import CreateAttachment


class TestAttachmentsApi:
    @pytest.fixture
    def create_attachment(self, test_data: str) -> CreateAttachment:
        return CreateAttachment(
            name="lorem.txt",
            data=test_data,
        )

    @pytest.fixture(autouse=True)
    def setup_function(
        self,
        aws_default_region: str,
        s3_resource,
        initialize_posts_table,
    ):
        s3_resource.create_bucket(
            Bucket="attachments",
            CreateBucketConfiguration={"LocationConstraint": aws_default_region},
        )

    def test_successfully_add_attachment(
        self,
        attachment: Attachment,
        create_attachment: CreateAttachment,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{posts[0].id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.headers["Location"]

    @pytest.mark.parametrize("publication_state", ["draft", "scheduled", "published"])
    def test_add_attachment_to_non_deleted_post_in_any_publication_state(
        self,
        publication_state: str,
        create_attachment: CreateAttachment,
        posts: list[Post],
        posts_table,
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        post = posts[0]
        if publication_state == "draft":
            posts_table.update_item(
                Key={"id": post.id},
                UpdateExpression="REMOVE published_at",
            )
        elif publication_state == "scheduled":
            posts_table.update_item(
                Key={"id": post.id},
                UpdateExpression="SET published_at = :published_at",
                ExpressionAttributeValues={
                    ":published_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()
                },
            )

        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        response = test_client.post(
            f"/api/v1/posts/{post.id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_cannot_add_attachment_to_deleted_post(
        self,
        create_attachment: CreateAttachment,
        posts: list[Post],
        posts_table,
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        post = posts[0]
        posts_table.update_item(
            Key={"id": post.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": datetime.now(UTC).isoformat()},
        )
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{post.id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_add_attachment_to_missing_post(
        self,
        create_attachment: CreateAttachment,
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{uuid.uuid4()}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=create_attachment.model_dump(by_alias=True),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_public_attachment_read_remains_unavailable_for_draft_post(
        self,
        post_with_attachment: Post,
        posts_table,
        test_client: TestClient,
    ):
        posts_table.update_item(
            Key={"id": post_with_attachment.id},
            UpdateExpression="REMOVE published_at",
        )

        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.fixture
    def unpublished_post_with_attachment(
        self, post_with_attachment: Post, posts_table, request: pytest.FixtureRequest
    ) -> Post:
        if request.param == "draft":
            posts_table.update_item(
                Key={"id": post_with_attachment.id},
                UpdateExpression="REMOVE published_at",
            )
        else:
            posts_table.update_item(
                Key={"id": post_with_attachment.id},
                UpdateExpression="SET published_at = :published_at",
                ExpressionAttributeValues={
                    ":published_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()
                },
            )
        return post_with_attachment

    @pytest.mark.parametrize(
        "unpublished_post_with_attachment", ["draft", "scheduled"], indirect=True
    )
    def test_authenticated_reads_return_the_attachments_of_an_unpublished_post(
        self,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        unpublished_post_with_attachment: Post,
        user_dict: dict[str, str | None],
    ):
        post = unpublished_post_with_attachment
        attachment_id = post.attachments[0].id
        base = f"/api/v1/posts/{post.id}/attachments"
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        headers = {"Authorization": f"Bearer {jwt_token}"}

        listing = test_client.get(base, headers=headers)
        single = test_client.get(f"{base}/{attachment_id}", headers=headers)
        download = test_client.get(
            f"{base}/{attachment_id}/download", headers=headers, follow_redirects=False
        )

        assert listing.status_code == status.HTTP_200_OK
        assert [item["id"] for item in listing.json()] == [attachment_id]
        assert single.status_code == status.HTTP_200_OK
        assert download.status_code == status.HTTP_302_FOUND

    @pytest.mark.parametrize(
        "unpublished_post_with_attachment", ["draft", "scheduled"], indirect=True
    )
    def test_anonymous_reads_still_hide_the_attachments_of_an_unpublished_post(
        self,
        test_client: TestClient,
        unpublished_post_with_attachment: Post,
    ):
        post = unpublished_post_with_attachment
        attachment_id = post.attachments[0].id
        base = f"/api/v1/posts/{post.id}/attachments"

        responses = [
            test_client.get(base),
            test_client.get(f"{base}/{attachment_id}"),
            test_client.get(f"{base}/{attachment_id}/download", follow_redirects=False),
        ]

        assert [r.status_code for r in responses] == [status.HTTP_404_NOT_FOUND] * 3

    def test_attachment_read_with_an_invalid_token_is_rejected(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments",
            headers={"Authorization": "Bearer not-a-jwt"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fail_to_add_attachment_due_to_bad_request(
        self,
        jwt_secret_ssm_param_value: str,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)

        response = test_client.post(
            f"/api/v1/posts/{post_with_attachment.id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        result = response.json()
        assert result["status"] == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert result["id"]
        assert result["message"]
        assert result["errors"]

    @pytest.mark.parametrize("data", ["not-base64!", ""])
    def test_rejects_invalid_or_empty_attachment_data(
        self,
        data: str,
        create_attachment: CreateAttachment,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        payload = create_attachment.model_dump(by_alias=True)
        payload["data"] = data

        response = test_client.post(
            f"/api/v1/posts/{posts[0].id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=payload,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        body = response.json()
        assert body["status"] == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert body["id"]
        assert body["message"]
        assert body["errors"]

    def test_validation_error_does_not_echo_the_rejected_payload(
        self,
        create_attachment: CreateAttachment,
        posts: list[Post],
        test_client: TestClient,
        user_dict: dict[str, str | None],
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token, _ = generate_jwt_token(jwt_secret_ssm_param_value, user_dict)
        payload = create_attachment.model_dump(by_alias=True)
        payload["data"] = "not-base64-payload!"

        response = test_client.post(
            f"/api/v1/posts/{posts[0].id}/attachments",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=payload,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "not-base64-payload!" not in response.text
        assert response.json()["errors"][0]["loc"] == ["body", "data"]

    def test_fail_to_add_attachment_due_to_unauthorized(
        self,
        create_attachment: CreateAttachment,
        post_with_attachment: Post,
        test_client: TestClient,
        user_dict: dict[str, str | None],
    ):
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
        body = response.json()
        url = body.pop("url")
        assert (
            body.items()
            <= post_with_attachment.attachments[0].model_dump(by_alias=True).items()
        )
        assert url == (
            f"/api/v1/posts/{post_with_attachment.id}/attachments/"
            f"{post_with_attachment.attachments[0].id}/download"
        )

    def test_download_redirects_to_fresh_signed_url(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        attachment = post_with_attachment.attachments[0]
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{attachment.id}/download",
            follow_redirects=False,
        )

        assert response.status_code == status.HTTP_302_FOUND
        assert response.headers["Cache-Control"] == "no-store"
        assert "X-Amz-Signature=" in response.headers["Location"]
        assert "X-Amz-Expires=3600" in response.headers["Location"]

    def test_download_returns_not_found_for_unknown_attachment(
        self,
        post_with_attachment: Post,
        test_client: TestClient,
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{uuid.uuid4()}/download",
            follow_redirects=False,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

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
        body = response.json()[0]
        url = body.pop("url")
        assert (
            body.items()
            <= post_with_attachment.model_dump(include=["attachments"], by_alias=True)[
                "attachments"
            ][0].items()
        )
        assert url == (
            f"/api/v1/posts/{post_with_attachment.id}/attachments/"
            f"{post_with_attachment.attachments[0].id}/download"
        )

    def test_successfully_get_empty_attachments(
        self,
        posts: list[Post],
        test_client: TestClient,
    ):
        response = test_client.get(f"/api/v1/posts/{posts[0].id}/attachments")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
