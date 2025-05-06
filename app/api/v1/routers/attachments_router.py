from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Response, status

from app.jwt_bearer import JWTBearer
from app.models.auth import JWTToken
from app.models.response import Attachment as AttachmentResponse
from app.schemas.attachment_schema import CreateAttachment
from app.services.attachment_service import AttachmentService

logger = Logger(utc=True)

attachment_service = AttachmentService()
jwt_bearer = JWTBearer()
router = APIRouter()


@router.post("")
async def add_attachment(
    create_attachment: CreateAttachment,
    post_uuid: str,
    token: JWTToken = Depends(jwt_bearer),
):
    attachment = attachment_service.add_attachment(
        post_uuid,
        create_attachment.name,
        create_attachment.data,
        (
            create_attachment.display_name
            if create_attachment.display_name
            else create_attachment.name
        ),
    )
    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/posts/{post_uuid}/attachments/{attachment.id}"},
    )


@router.get("/{attachment_uuid}", status_code=status.HTTP_200_OK)
async def get_attachment_by_uuid(
    post_uuid: str, attachment_uuid: str
) -> AttachmentResponse:
    return attachment_service.get_attachment_by_id(post_uuid, attachment_uuid)


@router.get("", status_code=status.HTTP_200_OK)
async def get_attachments(post_uuid: str):
    return attachment_service.get_attachments(post_uuid)
