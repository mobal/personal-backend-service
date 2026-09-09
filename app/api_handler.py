import uuid

import uvicorn
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging.logger import set_package_logger
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.api.v1.api import router as api_v1_router
from app.middlewares import (
    ClientValidationMiddleware,
    CorrelationIdMiddleware,
    RateLimitingMiddleware,
)
from app.models.response import ErrorResponse, ValidationErrorResponse
from app.services.rate_limiter_service import RateLimiterService
from app.settings import Settings

settings = Settings()

if settings.debug:
    set_package_logger()

logger = Logger()

OPENAPI_TAGS = [
    {
        "name": "posts",
        "description": (
            "Markdown blog posts. Read endpoints are public; create, update "
            "and delete require a valid JWT."
        ),
    },
    {
        "name": "attachments",
        "description": (
            "Attachments nested under a post (`/posts/{postUuid}/attachments`). "
            "Adding an attachment requires a valid JWT."
        ),
    },
    {
        "name": "system",
        "description": "Operational endpoints that are not part of the v1 API.",
    },
]

app = FastAPI(
    debug=settings.debug,
    title="Personal Backend Service",
    summary="A secure API for managing and publishing Markdown blog content",
    description=(
        "## Overview\n\n"
        "Personal Backend Service provides the backend for a Markdown-based "
        "blog. Posts are stored in DynamoDB and rendered as HTML when "
        "requested. Attachments are stored in S3, and publishing sends the "
        "original Markdown to a remote blog server over SFTP.\n\n"
        "## API conventions\n\n"
        "- All routes use the `/api/v1` prefix.\n"
        "- Request and response bodies use camelCase JSON.\n"
        "- Protected operations require an HS256 JWT.\n"
        "- Tokens may be sent as `Authorization: Bearer <token>` or "
        "`?token=<token>`.\n"
        "- Errors use `{status, id, message}`.\n"
        "- Validation errors additionally include an `errors` array.\n"
        "- Every response includes an `X-Correlation-ID` header.\n\n"
        "## Authentication\n\n"
        "Reading published content is public. Creating, updating, publishing, "
        "uploading attachments, and deleting content require authentication."
    ),
    version="1.0.0",
    license_info={
        "name": "Apache-2.0",
        "identifier": "Apache-2.0",
    },
    openapi_tags=OPENAPI_TAGS,
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(ClientValidationMiddleware)
app.add_middleware(
    RateLimitingMiddleware,
    rate_limiter_service=RateLimiterService(
        settings=settings,
    ),
)
app.add_middleware(GZipMiddleware)
app.include_router(api_v1_router)


@app.get(
    "/health",
    tags=["system"],
    summary="Liveness probe",
    description=(
        'Returns HTTP 200 with `{"status": "healthy"}` while the app is '
        "up. Used by container healthchecks and load balancer target groups."
    ),
)
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True)


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
def botocore_error_handler(request: Request, error: BotoCoreError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error) if settings.debug else "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.exception(f"Received botocore error {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.exception(f"Received http exception {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=error.status_code, id=error_id, message=error.detail)
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    logger.exception(f"Received request validation error {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(error),
                errors=error.errors(),
            )
        ),
        status_code=status_code,
    )


if __name__ == "__main__":
    uvicorn.run("app.api_handler:app", host="localhost", port=8080, reload=True)
