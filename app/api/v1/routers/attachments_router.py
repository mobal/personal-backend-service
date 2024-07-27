from io import BytesIO

from aws_lambda_powertools import Logger
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.jwt_bearer import JWTBearer
from app.services.storage_service import StorageService

logger = Logger(utc=True)

jwt_bearer = JWTBearer()
storage_service = StorageService()
router = APIRouter()


@router.get("/{bucket}/{key}", status_code=status.HTTP_200_OK)
async def get_attachment(bucket: str, key: str) -> StreamingResponse:
    response = StreamingResponse(
        BytesIO(await storage_service.get_object(bucket, key)),
        media_type="application/octet-stream",
    )
    response.headers["Content-Disposition"] = "attachment;"
    return response
