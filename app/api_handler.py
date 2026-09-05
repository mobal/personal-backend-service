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
    summary="Serverless personal blog backend",
    description=(
        "REST API for the personal blog: posts are stored as Markdown in "
        "DynamoDB and rendered to HTML on read, attachments live in S3 with "
        "public-read access, and published posts are pushed to a remote "
        "server over SFTP.\n\n"
        "Conventions:\n\n"
        "- All v1 routes are prefixed with `/api/v1` and exchange JSON in "
        "camelCase.\n"
        "- Mutating and deleting a resource requires a JWT (HS256), sent as "
        "`Authorization: Bearer <token>` or as `?token=<token>`.\n"
        "- Every error response uses the same envelope "
        "`{status, id, message}` (validation errors add an `errors` list).\n"
        "- The response of every request carries an `X-Correlation-ID` "
        "header.\n"
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
