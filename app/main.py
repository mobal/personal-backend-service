import logging
import uuid
from typing import List
from urllib.request import Request

import uvicorn
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi_camelcase import CamelModel
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.responses import JSONResponse

from app.api.api_v1.api import router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(router, prefix='/api/v1')

handler = Mangum(app)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[dict]


@app.exception_handler(ClientError)
async def client_error_handler(request: Request, error: ClientError):
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{error_message} with status_code={status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(status=status_code, id=error_id, message=error_message)),
        status_code=status_code
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException):
    error_id = uuid.uuid4()
    logger.error(f'{error.detail} with status_code={error.status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(status=error.status_code, id=error_id, message=error.detail)),
        status_code=error.status_code
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, error: ValidationError):
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(f'{error_message} with status_code={status_code}, error_id={error_id} and request={request}')
    return JSONResponse(
        content=jsonable_encoder(ValidationErrorResponse(status=status_code, id=error_id, message=str(error),
                                                         errors=error.errors())),
        status_code=status_code
    )


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
