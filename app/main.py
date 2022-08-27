import uuid
from typing import List

import uvicorn
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi_camelcase import CamelModel
from httpx import NetworkError
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import (
    HTTPException as StarletteHTTPException,
    ExceptionMiddleware,
)
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse

from app.api.v1.api import router
from app.settings import Settings

app = FastAPI(debug=True)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)
app.include_router(router, prefix='/api/v1')

settings = Settings()
logger = Logger()
metrics = Metrics()
tracer = Tracer()

handler = Mangum(app)
handler.__name__ = 'handler'
handler = tracer.capture_lambda_handler(handler)
handler = logger.inject_lambda_context(handler, clear_state=True)
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[dict]


@app.middleware('http')
async def correlation_id_middleware(request: Request, call_next) -> Response:
    correlation_id = request.headers.get('X-Correlation-ID')
    if not correlation_id:
        correlation_id = (
            request.scope.get('aws_context').aws_request_id
            if request.scope.get('aws_context')
            else str(uuid.uuid4())
        )
    logger.set_correlation_id(correlation_id)
    tracer.put_annotation(key='X-Correlation-ID', value=correlation_id)
    response = await call_next(request)
    response.headers['X-Correlation-ID'] = correlation_id
    return response


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
@app.exception_handler(NetworkError)
@app.exception_handler(Exception)
async def error_handler(request: Request, error) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = (
        str(error) if settings.app_stage == 'dev' else 'Internal Server Error'
    )
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{error_message} with {status_code=} and {error_id=}')
    metrics.add_metric(name='ClientErrorHandler', unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
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
@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, error: ValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(f'{error_message} with {status_code=} and {error_id=}')
    metrics.add_metric(name='ValidationErrorHandler', unit=MetricUnit.Count, value=1)
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


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
