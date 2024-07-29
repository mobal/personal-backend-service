import pytest
from fastapi import status
from starlette.testclient import TestClient

from app.models.post import Post

BASE_URL = "/api/v1/posts/{0}/attachments/{1}"


@pytest.mark.asyncio
class TestAttachmentsApi:
    async def test_successfully_get_attachment(
        self, post_with_attachment: Post, test_client: TestClient
    ):
        response = test_client.get(
            f"/api/v1/posts/{post_with_attachment.id}/attachments/{post_with_attachment.attachments[0].id}"
        )

        assert response.status_code == status.HTTP_200_OK
