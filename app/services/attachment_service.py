import base64
import binascii
import mimetypes
import re
import uuid
from urllib.parse import quote

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status
from unidecode import unidecode

from app.exceptions import AttachmentNotFoundException
from app.models.post import Attachment
from app.models.response import Attachment as AttachmentResponse
from app.schemas.attachment_schema import (
    MAX_ATTACHMENT_SIZE,
    MAX_ENCODED_ATTACHMENT_SIZE,
)
from app.services.post_service import PostService
from app.services.s3_storage_service import S3StorageService
from app.settings import Settings


class AttachmentService:
    def __init__(
        self,
        settings: Settings,
        post_service: PostService,
        storage_service: S3StorageService,
    ):
        self._settings = settings
        self._logger = Logger()
        self._post_service = post_service
        self._storage_service = storage_service

    def add_attachment(
        self, post_uuid: str, attachment_name: str, base64_data: str, display_name: str
    ) -> Attachment:
        attachment_name = unidecode(attachment_name).replace("\\", "/").split("/")[-1]
        attachment_name = re.sub(r"[^A-Za-z0-9._-]", "_", attachment_name).strip("._-")
        attachment_name = attachment_name[:180] or "attachment"
        safe_display_name = (
            "".join(
                char
                for char in display_name
                if char.isprintable() and char not in "\r\n"
            )[:180]
            or attachment_name
        )
        self._logger.info(f"Adding attachment {attachment_name=} to {post_uuid=}")

        post = self._post_service.get_post_by_uuid(post_uuid)
        mime_type = mimetypes.guess_type(attachment_name)[0]
        if mime_type is None:
            self._logger.info(
                f"Unknown MIME type for {attachment_name=}, defaulting to application/octet-stream"
            )
            mime_type = "application/octet-stream"
        attachment_id = str(uuid.uuid4())
        object_key = f"/{post.post_path}/{attachment_id}-{attachment_name}"

        if len(base64_data) > MAX_ENCODED_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Attachment exceeds maximum size of 5 MB",
            )
        try:
            file_data = base64.b64decode(base64_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Attachment data must be valid base64",
            ) from exc

        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Attachment must not be empty",
            )

        # Validate file size (5MB limit)
        if len(file_data) > MAX_ATTACHMENT_SIZE:
            error_msg = f"Attachment {attachment_name} exceeds maximum size of {MAX_ATTACHMENT_SIZE} bytes"
            self._logger.error(error_msg)
            raise ValueError(error_msg)

        self._storage_service.put_object(
            self._settings.attachments_bucket_name,
            object_key,
            file_data,
            content_type=mime_type,
            content_disposition=(
                f"attachment; filename*=UTF-8''{quote(safe_display_name, safe='')}"
            ),
        )

        attachment = Attachment(
            id=attachment_id,
            bucket=self._settings.attachments_bucket_name,
            content_length=len(file_data),
            display_name=safe_display_name,
            mime_type=mime_type,
            name=object_key,
            region=self._settings.aws_region,
        )

        updated_attachments = list(post.attachments or []) + [attachment]
        self._post_service.update_post(
            post_uuid,
            {
                "attachments": [
                    att.model_dump(exclude_none=True) for att in updated_attachments
                ]
            },
        )

        return attachment

    def get_attachments(self, post_uuid: str) -> list[AttachmentResponse]:
        self._logger.info(f"Get attachments for {post_uuid=}")
        post = self._post_service.get_post(post_uuid)
        return (
            [
                AttachmentResponse(**attachment.model_dump())
                for attachment in post.attachments or []
            ]
            if post.attachments
            else []
        )

    def get_attachment_by_id(
        self, post_uuid: str, attachment_uuid: str
    ) -> AttachmentResponse:
        self._logger.info(f"Get attachment {attachment_uuid=} from {post_uuid=}")
        post = self._post_service.get_post(post_uuid)
        attachment = next(
            (
                attachment
                for attachment in post.attachments or []
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

    def get_attachment_download_url(self, post_uuid: str, attachment_uuid: str) -> str:
        post = self._post_service.get_published_post_by_uuid(post_uuid)
        attachment = next(
            (
                attachment
                for attachment in post.attachments or []
                if attachment.id == attachment_uuid
            ),
            None,
        )
        if attachment is None:
            raise AttachmentNotFoundException(
                f"The requested {attachment_uuid=} was not found for {post_uuid=}"
            )
        return self._storage_service.generate_presigned_download_url(
            attachment.bucket, attachment.name
        )
