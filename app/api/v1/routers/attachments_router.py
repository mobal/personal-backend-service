from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Response, status

from app.api.decorators import authorize
from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken, Role
from app.models.post import Attachment
from app.schemas.attachment_schema import CreateAttachment
from app.services.attachment_service import AttachmentService

logger = Logger(utc=True)

attachment_service = AttachmentService()
jwt_bearer = JWTBearer()
router = APIRouter()


@router.post("")
@authorize(roles=[Role.ATTACHMENT_CREATE])
async def add_attachment(
    create_attachment: CreateAttachment,
    post_uuid: str,
    token: JWTToken = Depends(jwt_bearer),
):
    attachment = await attachment_service.add_attachment(
        post_uuid, create_attachment.name, create_attachment.data
    )
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/posts/{post_uuid}/attachments/{attachment.id}"},
    )


@router.get("/{attachment_uuid}", status_code=status.HTTP_200_OK)
async def get_attachment(post_uuid: str, attachment_uuid: str) -> Attachment:
    return await attachment_service.get_attachment_by_id(post_uuid, attachment_uuid)


@router.get("", status_code=status.HTTP_200_OK)
async def get_attachments(post_uuid: str):
    return await attachment_service.get_attachments(post_uuid)
