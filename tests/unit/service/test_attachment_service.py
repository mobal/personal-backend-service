import base64
import copy
import uuid
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture

from app.exceptions import AttachmentNotFoundException, PostNotFoundException
from app.models.post import Attachment, Post
from app.models.response import Attachment as AttachmentResponse
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.s3_storage_service import S3StorageService

ATTACHMENT_NAME = "lorem.txt"
UNKNOWN_EXT = "lorem.xyz"


class TestAttachmentService:
    def test_successfully_add_attachment(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
        assert result.url
        post_service.get_post.assert_called_once_with(posts[0].id)
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
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
        assert result.url
        post_service.get_post.assert_called_once_with(posts[0].id)
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
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)
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
        post_service.get_post.assert_called_once_with(post_with_attachment.id)
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

    def test_fail_to_add_attachment_due_to_post_not_found(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        test_data: bytes,
    ):
        mocker.patch.object(
            PostService, "get_post", side_effect=PostNotFoundException()
        )

        with pytest.raises(PostNotFoundException) as exc_info:
            encoded_data = base64.b64encode(test_data).decode("utf-8")
            attachment_service.add_attachment(
                posts[0].id, ATTACHMENT_NAME, encoded_data, ATTACHMENT_NAME
            )

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    def test_successfully_get_attachments(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        attachments = attachment_service.get_attachments(post_with_attachment.id)

        assert attachments[0].model_dump().items() <= attachment.model_dump().items()
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
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        post_attachment = attachment_service.get_attachment_by_id(
            post_with_attachment.id, attachment.id
        )

        assert AttachmentResponse(**attachment.model_dump()) == post_attachment
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
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        with pytest.raises(AttachmentNotFoundException) as exc_info:
            attachment_service.get_attachment_by_id(
                post_with_attachment.id, str(uuid.uuid4())
            )

        assert exc_info.type == AttachmentNotFoundException
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    def test_successfully_add_attachment_with_unknown_mime_type(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        s3_storage_service: S3StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
        post_service.get_post.assert_called_once_with(posts[0].id)
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
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
        assert result.url
        post_service.get_post.assert_called_once_with(posts[0].id)
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
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
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
