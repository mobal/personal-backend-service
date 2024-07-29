from aws_lambda_powertools import Logger
from fastapi import APIRouter, status

from app.api.decorators import authorize
from app.jwt_bearer import JWTBearer
from app.models.auth import Role
from app.models.post import Attachment
from app.schemas.attachment_schema import CreateAttachment
from app.services.attachment_service import AttachmentService

logger = Logger(utc=True)

attachment_service = AttachmentService()
jwt_bearer = JWTBearer()
router = APIRouter()


@authorize(roles=[Role.ATTACHMENT_CREATE])
@router.post("", status_code=status.HTTP_201_CREATED)
async def add_attachment(create_attachment: CreateAttachment, post_uuid: str):
    return await attachment_service.add_attachment(
        post_uuid, create_attachment.name, create_attachment.data
    )


@router.get("/{uuid}", status_code=status.HTTP_200_OK)
async def get_attachment(post_uuid: str, attachment_uuid: str) -> Attachment:
    return await attachment_service.get_attachment_by_id(post_uuid, attachment_uuid)


@router.get("", status_code=status.HTTP_201_CREATED)
async def get_attachments(post_uuid: str):
    return await attachment_service.get_attachments(post_uuid)
