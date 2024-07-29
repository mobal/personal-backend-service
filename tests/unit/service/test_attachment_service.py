import uuid
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture

from app.exceptions import AttachmentNotFoundException, PostNotFoundException
from app.models.post import Attachment, Post
from app.services.attachment_service import AttachmentService
from app.services.post_service import PostService
from app.services.storage_service import StorageService


class TestAttachmentService:
    async def test_successfully_add_attachment(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        storage_service: StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post", return_value=posts[0])
        mocker.patch.object(
            StorageService,
            "put_object",
            return_value={
                "ContentLength": len(test_data.decode()),
                "ContentType": "plain/text",
            },
        )
        mocker.patch.object(PostService, "update_post")

        await attachment_service.add_attachment(posts[0].id, attachment.name, test_data)

        post_service.get_post.assert_called_once_with(posts[0].id)
        storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once_with(posts[0].id, ANY)

    async def test_successfully_extend_attachments(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
        storage_service: StorageService,
        test_data: bytes,
    ):
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)
        mocker.patch.object(
            StorageService,
            "put_object",
            return_value={"ContentLength": len(test_data), "ContentType": "plain/text"},
        )
        mocker.patch.object(PostService, "update_post")

        await attachment_service.add_attachment(
            post_with_attachment.id, attachment.name, test_data.decode()
        )

        post_service.get_post.assert_called_once_with(post_with_attachment.id)
        storage_service.put_object.assert_called_once()
        post_service.update_post.assert_called_once_with(post_with_attachment.id, ANY)

    async def test_fail_to_add_attachment_due_to_post_not_found(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        posts: list[Post],
        test_data: bytes,
    ):
        mocker.patch.object(
            PostService, "get_post", side_effect=PostNotFoundException()
        )

        with pytest.raises(PostNotFoundException) as exc_info:
            await attachment_service.add_attachment(
                posts[0].id, attachment.name, test_data.decode()
            )

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    async def test_successfully_get_attachments(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        attachments = await attachment_service.get_attachments(post_with_attachment.id)

        assert attachments == [attachment]
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    async def test_fail_to_get_attachments_due_to_post_not_found(
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
            await attachment_service.get_attachments(posts[0].id)

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    async def test_successfully_get_attachment_by_name(
        self,
        mocker: MockerFixture,
        attachment: Attachment,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        attachment = await attachment_service.get_attachment_by_id(
            post_with_attachment.id, attachment.id
        )

        assert attachment == attachment
        post_service.get_post.assert_called_once_with(post_with_attachment.id)

    async def test_fail_to_get_attachment_by_name_due_to_post_not_found(
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
            await attachment_service.get_attachment_by_id(posts[0].id, attachment.id)

        assert exc_info.type == PostNotFoundException
        post_service.get_post.assert_called_once_with(posts[0].id)

    async def test_fail_to_get_attachment_by_name_due_to_not_found(
        self,
        mocker: MockerFixture,
        attachment_service: AttachmentService,
        post_service: PostService,
        post_with_attachment: Post,
    ):
        mocker.patch.object(PostService, "get_post", return_value=post_with_attachment)

        with pytest.raises(AttachmentNotFoundException) as exc_info:
            await attachment_service.get_attachment_by_id(
                post_with_attachment.id, str(uuid.uuid4())
            )

        assert exc_info.type == AttachmentNotFoundException
        post_service.get_post.assert_called_once_with(post_with_attachment.id)
