import base64
import mimetypes
import uuid

from aws_lambda_powertools import Logger
from unidecode import unidecode

from app import settings
from app.exceptions import AttachmentNotFoundException
from app.models.post import Attachment
from app.models.response import Attachment as AttachmentResponse
from app.services.post_service import PostService
from app.services.storage_service import StorageService


class AttachmentService:
    def __init__(self):
        self._logger = Logger(utc=True)
        self._post_service = PostService()
        self._storage_service = StorageService()

    async def add_attachment(
        self, post_uuid: str, attachment_name: str, base64_data: str, display_name: str
    ) -> Attachment:
        attachment_name = unidecode(attachment_name)
        self._logger.info(f"Adding attachment {attachment_name=} to {post_uuid=}")

        post = await self._post_service.get_post(post_uuid)
        mime_type = mimetypes.guess_type(attachment_name)[0]
        object_key = f"/{post.post_path}/{attachment_name}"

        file_data = base64.b64decode(base64_data)
        await self._storage_service.put_object(
            settings.attachments_bucket_name, object_key, file_data
        )

        attachment = Attachment(
            id=str(uuid.uuid4()),
            bucket=settings.attachments_bucket_name,
            content_length=len(base64_data),
            display_name=display_name,
            mime_type=mime_type,
            name=object_key,
        )

        updated_attachments = list(post.attachments or []) + [attachment]
        await self._post_service.update_post(
            post_uuid,
            {
                "attachments": [
                    att.model_dump(exclude_none=True) for att in updated_attachments
                ]
            },
        )

        return attachment

    async def get_attachments(self, post_uuid: str) -> list[AttachmentResponse]:
        self._logger.info(f"Get attachments for {post_uuid=}")
        post = await self._post_service.get_post(post_uuid)
        return (
            [
                AttachmentResponse(**attachment.model_dump())
                for attachment in post.attachments
            ]
            if post.attachments
            else []
        )

    async def get_attachment_by_id(
        self, post_uuid: str, attachment_uuid: str
    ) -> AttachmentResponse:
        self._logger.info(f"Get attachment {attachment_uuid=} from {post_uuid=}")
        post = await self._post_service.get_post(post_uuid)
        attachment = next(
            (
                attachment
                for attachment in post.attachments
                if attachment.id == attachment_uuid
            ),
            None,
        )
        if attachment is None:
            error_message = (
                f"The requested {attachment_uuid=} was not found for {post_uuid=}"
            )
            self._logger.exception(error_message)
            raise AttachmentNotFoundException(error_message)
        return AttachmentResponse(**attachment.model_dump())
