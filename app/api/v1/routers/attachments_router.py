from typing import Annotated

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Path, Response, status

from app.dependencies import get_attachment_service, get_jwt_bearer
from app.models.auth import JWTToken
from app.models.response import (
    Attachment as AttachmentResponse,
    ErrorResponse,
    ValidationErrorResponse,
)
from app.schemas.attachment_schema import CreateAttachment
from app.services.attachment_service import AttachmentService

logger = Logger()

router = APIRouter()

# Shared OpenAPI response definitions. Error handlers wrap every failure in
# the ErrorResponse envelope (ValidationErrorResponse for 422).
RESPONSE_403 = {403: {"model": ErrorResponse, "description": "Missing or invalid JWT"}}
RESPONSE_404_POST = {404: {"model": ErrorResponse, "description": "Post not found"}}
RESPONSE_404_ATTACHMENT = {
    404: {"model": ErrorResponse, "description": "Attachment not found"}
}
RESPONSE_422 = {
    422: {
        "model": ValidationErrorResponse,
        "description": "Request body failed validation",
    }
}

POST_UUID = Path(
    description="UUID of the post the attachment belongs to",
    examples=["84898870-a3f6-45b7-b2af-542728b2d290"],
)
ATTACHMENT_UUID = Path(
    description="UUID of the attachment",
    examples=["00fc23e8-e3a9-48e2-869a-ae2ec4abd36e"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={**RESPONSE_403, **RESPONSE_404_POST, **RESPONSE_422},
    summary="Add an attachment to a post",
    description=(
        "Uploads a file (base64-encoded, up to 5 MB) to S3 and links it to "
        "the post. The MIME type is guessed from the file extension. Requires "
        "a valid JWT. On success the response body is empty and the new "
        "attachment is addressed in the `Location` header."
    ),
    response_description="Created — the response body is empty; the new "
    "attachment is addressed in the Location header",
)
def add_attachment(
    create_attachment: CreateAttachment,
    post_uuid: Annotated[str, POST_UUID],
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


@router.get(
    "/{attachment_uuid}",
    status_code=status.HTTP_200_OK,
    responses={**RESPONSE_404_POST, **RESPONSE_404_ATTACHMENT, **RESPONSE_422},
    summary="Get an attachment by UUID",
    description=(
        "Returns the metadata of one attachment (including its public URL); "
        "the binary content is served from S3 directly."
    ),
)
def get_attachment_by_uuid(
    post_uuid: Annotated[str, POST_UUID],
    attachment_uuid: Annotated[str, ATTACHMENT_UUID],
    attachment_service: Annotated[AttachmentService, Depends(get_attachment_service)],
) -> AttachmentResponse:
    return attachment_service.get_attachment_by_id(post_uuid, attachment_uuid)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[AttachmentResponse],
    responses={**RESPONSE_404_POST, **RESPONSE_422},
    summary="List attachments of a post",
    description="Returns the metadata (including public URLs) of every "
    "attachment linked to the post.",
)
def get_attachments(
    post_uuid: Annotated[str, POST_UUID],
    attachment_service: Annotated[AttachmentService, Depends(get_attachment_service)],
) -> list[AttachmentResponse]:
    return attachment_service.get_attachments(post_uuid)
