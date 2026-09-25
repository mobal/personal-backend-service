import base64
import copy
import uuid
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture

from app.exceptions import AttachmentNotFoundException, PostNotFoundException
from app.models.post import Attachment, Post
from app.models.response import (
    Attachment as AttachmentResponse,
    Post as PostResponse,
)
from app.schemas.attachment_schema import MAX_ENCODED_ATTACHMENT_SIZE, CreateAttachment
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.s3_storage_service import S3StorageService

ATTACHMENT_NAME = "lorem.txt"
UNKNOWN_EXT = "lorem.xyz"


def post_response_with_attachment(attachment: Attachment) -> PostResponse:
    return PostResponse(
        attachments=[
            AttachmentResponse(
                id=attachment.id,
                content_length=attachment.content_length,
                description=attachment.description,
                display_name=attachment.display_name,
                mime_type=attachment.mime_type,
                url="https://example.com/signed-download",
            )
        ]
    )


class TestAttachmentService:
    def test_rejects_oversized_encoded_data_before_decoding(self, mocker):
        decode = mocker.patch("app.schemas.attachment_schema.base64.b64decode")

        with pytest.raises(ValueError, match="maximum size"):
            CreateAttachment(
                name="large.bin", data="A" * (MAX_ENCODED_ATTACHMENT_SIZE + 1)
            )

        decode.assert_not_called()

    def test_successfully_add_attachment(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={
                "ContentLength": len(test_data),
                "ContentType": "plain/text",
            },
        )
        mocker.patch.object(PostService, "update_post")

        encoded_data = base64.b64encode(test_data).decode("utf-8")
        result = attachment_service.add_attachment(
            posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
        )

        assert result.bucket == "attachments"
        assert result.content_length == len(test_data)
        assert result.display_name == ATTACHMENT_NAME
        assert result.name
        assert "url" not in result.model_dump()
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        s3_storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once_with(
            posts[0].id, {"attachments": [result.model_dump(exclude_none=True)]}
        )

    def test_successfully_add_attachment_with_custom_display_name(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={
                "ContentLength": len(test_data.decode()),
                "ContentType": "plain/text",
            },
        )
        mocker.patch.object(PostService, "update_post")

        encoded_data = base64.b64encode(test_data).decode("utf-8")
        result = attachment_service.add_attachment(
            posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
        )

        assert result.bucket == "attachments"
        assert result.content_length == len(test_data)
        assert result.display_name == ATTACHMENT_NAME
        assert result.name
        assert "url" not in result.model_dump()
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        s3_storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once_with(posts[0].id, ANY)

    def test_successfully_extend_attachments(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(
            PostService, "get_post_by_uuid", return_value=post_with_attachment
        )
        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={"ContentLength": len(test_data), "ContentType": "plain/text"},
        )
        mocker.patch.object(PostService, "update_post")

        encoded_data = base64.b64encode(test_data).decode("utf-8")
        result = attachment_service.add_attachment(
            post_with_attachment.id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
        )

        assert post_with_attachment.attachments
        post_service.get_post_by_uuid.assert_called_once_with(post_with_attachment.id)
        s3_storage_service.put_object.assert_called_once()
        extended_attachments = copy.deepcopy(post_with_attachment.attachments)
        extended_attachments.append(result)
        post_service.update_post.assert_called_once_with(
            post_with_attachment.id,
            {
                "attachments": [
                    attachment.model_dump(exclude_none=True)
                    for attachment in extended_attachments
                ]
            },
        )

    def test_sanitizes_object_name_and_sets_safe_content_metadata(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(PostService, "update_post")
        mocker.patch.object(S3StorageService, "put_object")

        result = attachment_service.add_attachment(
            posts[0].id,
            "../../hello world.txt",
            base64.b64encode(test_data).decode("ascii"),
            'report"\r\nX-Evil: true.txt',
        )

        assert result.name.endswith("-hello_world.txt")
        assert ".." not in result.name
        call = s3_storage_service.put_object.call_args
        assert call.kwargs == {
            "content_type": "text/plain",
            "content_disposition": (
                "attachment; filename*=UTF-8''report%22X-Evil%3A%20true.txt"
            ),
        }

    def test_fail_to_add_attachment_due_to_post_not_found(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        test_data: bytes,
    ):
        mocker.patch.object(
            PostService, "get_post_by_uuid", side_effect=PostNotFoundException()
        )

        with pytest.raises(PostNotFoundException) as exc_info:
            encoded_data = base64.b64encode(test_data).decode("utf-8")
            attachment_service.add_attachment(
                posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
            )

        assert exc_info.type == PostNotFoundException
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)

    def test_successfully_get_attachments(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(
            PostService,
            "get_post",
            return_value=post_response_with_attachment(attachment),
        )

        attachments = attachment_service.get_attachments(post_with_attachment.id)

        assert attachments == post_response_with_attachment(attachment).attachments
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    def test_successfully_get_attachments_when_none(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
    ):
        mocker.patch.object(PostService, "get_post", return_value=posts[0])

        attachments = attachment_service.get_attachments(posts[0].id)

        assert attachments == []

    def test_fail_to_get_attachments_due_to_post_not_found(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
    ):
        mocker.patch.object(
            PostService, "get_post", side_effect=PostNotFoundException()
        )

        with pytest.raises(PostNotFoundException) as exc_info:
            attachment_service.get_attachments(posts[0].id)

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    def test_successfully_get_attachment_by_name(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(
            PostService,
            "get_post",
            return_value=post_response_with_attachment(attachment),
        )

        post_attachment = attachment_service.get_attachment_by_id(
            post_with_attachment.id, attachment.id
        )

        assert post_response_with_attachment(attachment).attachments == [
            post_attachment
        ]
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    def test_fail_to_get_attachment_by_name_due_to_post_not_found(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
    ):
        mocker.patch.object(
            PostService, "get_post", side_effect=PostNotFoundException()
        )

        with pytest.raises(PostNotFoundException) as exc_info:
            attachment_service.get_attachment_by_id(posts[0].id, attachment.id)

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    def test_fail_to_get_attachment_by_name_due_to_not_found(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(
            PostService,
            "get_post",
            return_value=post_response_with_attachment(attachment),
        )

        with pytest.raises(AttachmentNotFoundException) as exc_info:
            attachment_service.get_attachment_by_id(
                post_with_attachment.id, str(uuid.uuid4())
            )

        assert exc_info.type == AttachmentNotFoundException
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    def test_fail_to_get_attachment_when_post_has_no_attachments(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
    ):
        mocker.patch.object(PostService, "get_post", return_value=PostResponse())

        with pytest.raises(AttachmentNotFoundException):
            attachment_service.get_attachment_by_id(posts[0].id, str(uuid.uuid4()))

        post_service.get_post.assert_called_once_with(posts[0].id)

    def test_download_url_signs_published_attachment_on_demand(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
        s3_storage_service: S3StorageService,
    ):
        attachment = post_with_attachment.attachments[0]
        mocker.patch.object(
            PostService, "get_published_post_by_uuid", return_value=post_with_attachment
        )
        mocker.patch.object(
            S3StorageService,
            "generate_presigned_download_url",
            return_value="https://example.com/signed-download",
        )

        result = attachment_service.get_attachment_download_url(
            post_with_attachment.id, attachment.id
        )

        assert result == "https://example.com/signed-download"
        post_service.get_published_post_by_uuid.assert_called_once_with(
            post_with_attachment.id
        )
        s3_storage_service.generate_presigned_download_url.assert_called_once_with(
            attachment.bucket, attachment.name
        )

    def test_download_url_rejects_unknown_attachment(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_with_attachment: Post,
        s3_storage_service: S3StorageService,
    ):
        mocker.patch.object(
            PostService, "get_published_post_by_uuid", return_value=post_with_attachment
        )
        mocker.patch.object(S3StorageService, "generate_presigned_download_url")

        with pytest.raises(AttachmentNotFoundException):
            attachment_service.get_attachment_download_url(
                post_with_attachment.id, str(uuid.uuid4())
            )

        s3_storage_service.generate_presigned_download_url.assert_not_called()

    def test_successfully_add_attachment_with_unknown_mime_type(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={
                "ContentLength": len(test_data),
                "ContentType": "application/octet-stream",
            },
        )
        mocker.patch.object(PostService, "update_post")

        result = attachment_service.add_attachment(
            posts[0].id, "test.foo", test_data.decode(), "test.foo"
        )

        assert result.mime_type == "application/octet-stream"
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        s3_storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once_with(
            posts[0].id, {"attachments": [result.model_dump(exclude_none=True)]}
        )

    def test_fail_to_add_attachment_due_to_file_too_large(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(PostService, "update_post")

        large_data = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
        encoded_data = base64.b64encode(large_data).decode("utf-8")

        with pytest.raises(ValueError) as exc_info:
            attachment_service.add_attachment(
                posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
            )

        assert "exceeds maximum size" in str(exc_info.value)
        assert "5242880" in str(exc_info.value)  # 5MB in bytes

    def test_successfully_add_attachment_under_limit(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={
                "ContentLength": len(test_data),
                "ContentType": "plain/text",
            },
        )
        mocker.patch.object(PostService, "update_post")

        encoded_data = base64.b64encode(test_data).decode("utf-8")
        result = attachment_service.add_attachment(
            posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
        )

        assert result.bucket == "attachments"
        assert result.content_length == len(test_data)
        assert result.display_name == ATTACHMENT_NAME
        assert result.name
        assert "url" not in result.model_dump()
        post_service.get_post_by_uuid.assert_called_once_with(posts[0].id)
        s3_storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once()

    def test_add_attachment_with_exactly_5mb(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
    ):
        """Test that adding an attachment exactly 5MB succeeds."""
        mocker.patch.object(PostService, "get_post_by_uuid", return_value=posts[0])
        mocker.patch.object(PostService, "update_post")

        exact_5mb_data = b"x" * (5 * 1024 * 1024)
        encoded_data = base64.b64encode(exact_5mb_data).decode("utf-8")

        mocker.patch.object(
            S3StorageService,
            "put_object",
            return_value={
                "ContentLength": len(exact_5mb_data),
                "ContentType": "plain/text",
            },
        )

        result = attachment_service.add_attachment(
            posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
        )

        assert result.content_length == len(exact_5mb_data)
        assert result.content_length == 5 * 1024 * 1024
        s3_storage_service.put_object.assert_called_once()
