import logging
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger()

X_CORRELATION_ID = 'X-Correlation-ID'


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(X_CORRELATION_ID)
        if not correlation_id:
            correlation_id = (
                request.scope['aws.context'].aws_request_id
                if request.scope.get('aws.context')
                else str(uuid.uuid4())
            )
        logger.set_correlation_id = correlation_id
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id
        return response
