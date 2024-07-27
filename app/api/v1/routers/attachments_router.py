from aws_lambda_powertools import Logger
from fastapi import APIRouter, status

from app.jwt_bearer import JWTBearer
from app.models.post import Attachment
from app.services.attachment_service import AttachmentService

logger = Logger(utc=True)

attachment_service = AttachmentService()
jwt_bearer = JWTBearer()
router = APIRouter()


@router.get("/{attachment_name}", status_code=status.HTTP_200_OK)
async def get_attachment(post_uuid: str, attachment_name: str) -> Attachment:
    return await attachment_service.get_attachment(post_uuid, attachment_name)
