import logging
import uuid
from urllib.request import Request

from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from mangum import Mangum
from starlette import status
from starlette.responses import JSONResponse

from app.api.v1.router import router as api_v1_router

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(api_v1_router, prefix='/api/v1')

handler = Mangum(app)


@app.exception_handler(ClientError)
async def validation_exception_handler(request: Request, error: ClientError):
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{error_message} with status code {status_code} and error id {error_id}')
    return JSONResponse(content=jsonable_encoder({'status': status_code, 'id': error_id, 'message': error_message}),
                        status_code=status_code)
