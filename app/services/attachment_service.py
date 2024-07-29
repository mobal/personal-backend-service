import base64
import uuid

from aws_lambda_powertools import Logger
from unidecode import unidecode

from app.exceptions import AttachmentNotFoundException
from app.models.post import Attachment
from app.services.post_service import PostService
from app.services.storage_service import StorageService


class AttachmentService:
    def __init__(self):
        self.__logger = Logger(utc=True)
        self.__post_service = PostService()
        self.__storage_service = StorageService()

    async def add_attachment(
        self, post_uuid: str, attachment_name: str, base64_data: str
    ):
        attachment_name = unidecode(attachment_name)
        self.__logger.info(f"Add attachment {attachment_name=} to {post_uuid=}")
        post = await self.__post_service.get_post(post_uuid)
        object_key = f"{post.post_path}/{attachment_name}"
        response = await self.__storage_service.put_object(
            "attachments", object_key, base64.b64decode(base64_data)
        )
        attachments = []
        if post.attachments:
            attachments.extend(post.attachments)
        attachments.append(
            Attachment(
                id=str(uuid.uuid4()),
                bucket="attachments",
                content_length=response["ContentLength"],
                content_type=response["ContentType"],
                name=object_key,
            )
        )
        await self.__post_service.update_post(
            post_uuid, {"attachments": post.attachments}
        )

    async def get_attachments(self, post_uuid: str) -> list[Attachment]:
        self.__logger.info(f"Get attachments for {post_uuid=}")
        return (await self.__post_service.get_post(post_uuid)).attachments

    async def get_attachment_by_id(self, post_uuid: str, attachment_uuid: str):
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
        return attachment
