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
        self.__logger = Logger(utc=True)
        self.__post_service = PostService()
        self.__storage_service = StorageService()

    async def add_attachment(
        self, post_uuid: str, attachment_name: str, base64_data: str, display_name: str
    ) -> Attachment:
        attachment_name = unidecode(attachment_name)
        self.__logger.info(f"Add attachment {attachment_name=} to {post_uuid=}")
        post = await self.__post_service.get_post(post_uuid)
        mime_type, _ = mimetypes.guess_type(attachment_name)
        object_key = f"/{post.post_path}/{attachment_name}"
        await self.__storage_service.put_object(
            settings.attachments_bucket_name, object_key, base64.b64decode(base64_data)
        )
        attachments = []
        if post.attachments:
            attachments.extend(post.attachments)
        attachment = Attachment(
            id=str(uuid.uuid4()),
            bucket=settings.attachments_bucket_name,
            content_length=len(base64_data),
            display_name=display_name,
            mime_type=mime_type,
            name=object_key,
        )
        attachments.append(attachment)
        await self.__post_service.update_post(
            post_uuid,
            {
                "attachments": [
                    attachment.model_dump(exclude_none=True)
                    for attachment in attachments
                ]
            },
        )
        return attachment

    async def get_attachments(self, post_uuid: str) -> list[AttachmentResponse]:
        self.__logger.info(f"Get attachments for {post_uuid=}")
        post = await self.__post_service.get_post(post_uuid)
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
        self.__logger.info(f"Get attachment {attachment_uuid=} from {post_uuid=}")
        post = await self.__post_service.get_post(post_uuid)
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
            self.__logger.exception(error_message)
            raise AttachmentNotFoundException(error_message)
        return AttachmentResponse(**attachment.model_dump())
