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
from fastapi_camelcase import CamelModel
from mangum import Mangum
from starlette import status
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse

from app.api.v1.api import router
from app.middlewares import CorrelationIdMiddleware
from app.settings import Settings

settings = Settings()

if settings.debug:
    set_package_logger()

logger = Logger(utc=True)
metrics = Metrics()
tracer = Tracer()

app = FastAPI(debug=settings.debug, title='PersonalBackendApp', version='1.0.0')
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.include_router(router, prefix='/api/v1')

handler = Mangum(app)
handler.__name__ = 'handler'
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
    error_message = str(error) if settings.debug else 'Internal Server Error'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{str(error)} with {status_code=} and {error_id=}')
    metrics.add_metric(name='ErrorHandler', unit=MetricUnit.Count, value=1)
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
    logger.error(f'{error.detail} with {error.status_code=} and {error_id=}')
    metrics.add_metric(name='HttpExceptionHandler', unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=error.status_code, id=error_id, message=error.detail)
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(exc)
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    logger.error(f'{error_message} with {status_code=} and {error_id=}')
    metrics.add_metric(name='ValidationErrorHandler', unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(exc),
                errors=exc.errors(),
            )
        ),
        status_code=status_code,
    )


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=8080, reload=True)
