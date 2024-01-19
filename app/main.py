import uuid
from typing import List

import uvicorn
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging.logger import set_package_logger
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from mangum import Mangum
from starlette import status
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse

from app.api.v1.api import router as api_v1_router
from app.middlewares import CorrelationIdMiddleware
from app.models.camel_model import CamelModel
from app.settings import Settings

settings = Settings()

if settings.debug:
    set_package_logger()

logger = Logger(utc=True)
metrics = Metrics()
tracer = Tracer()

app = FastAPI(debug=settings.debug, title="PersonalBackendApp", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.include_router(api_v1_router)

handler = Mangum(app)
handler.__name__ = "handler"
handler = tracer.capture_lambda_handler(handler)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[dict]


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
async def botocore_error_handler(
    request: Request, error: BotoCoreError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error) if settings.debug else "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.exception(f"Received botocore error {error_id=}")
    metrics.add_metric(name="BotocoreErrorHandler", unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.exception(f"Received http exception {error_id=}")
    metrics.add_metric(name="HttpExceptionHandler", unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=error.status_code, id=error_id, message=error.detail)
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    logger.exception(f"Received request validation error {error_id=}")
    metrics.add_metric(
        name="RequestValidationErrorHandler", unit=MetricUnit.Count, value=1
    )
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
    uvicorn.run("app.main:app", host="localhost", port=8080, reload=True)
