from typing import Annotated

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_attachment_service, get_jwt_bearer
from app.models.auth import JWTToken
from app.models.response import Attachment as AttachmentResponse
from app.schemas.attachment_schema import CreateAttachment
from app.services.attachment_service import AttachmentService

logger = Logger()

router = APIRouter()


@router.post("")
def add_attachment(
    create_attachment: CreateAttachment,
    post_uuid: str,
    attachment_service: Annotated[AttachmentService, Depends(get_attachment_service)],
    token: Annotated[JWTToken, Depends(get_jwt_bearer)],
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
def get_attachment_by_uuid(
    post_uuid: str,
    attachment_uuid: str,
    attachment_service: Annotated[AttachmentService, Depends(get_attachment_service)],
) -> AttachmentResponse:
    return attachment_service.get_attachment_by_id(post_uuid, attachment_uuid)


@router.get("", status_code=status.HTTP_200_OK)
def get_attachments(
    post_uuid: str,
    attachment_service: Annotated[AttachmentService, Depends(get_attachment_service)],
):
    return attachment_service.get_attachments(post_uuid)
