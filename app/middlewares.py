import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta

from aws_lambda_powertools import Logger
from starlette import status
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app import Settings

X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str | None] = ContextVar(
    X_CORRELATION_ID, default=str(uuid.uuid4())
)
settings = Settings()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = Logger(utc=True)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get(X_CORRELATION_ID):
            correlation_id.set(request.headers[X_CORRELATION_ID])
        self._logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    RATE_LIMIT_DURATION = timedelta(seconds=settings.rate_limit_duration)

    def __init__(self, app):
        super().__init__(app)
        self.requests = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if settings.debug is False:
            client_ip = request.client.host
            request_count, last_request = self.requests.get(
                client_ip, (0, datetime.min)
            )
            elapsed_time = datetime.now() - last_request
            if elapsed_time > self.RATE_LIMIT_DURATION:
                request_count = 1
            else:
                if request_count >= settings.rate_limit_requests:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "message": "Rate limit exceeded. Please try again later"
                        },
                    )
                request_count += 1
            self.requests[client_ip] = (request_count, datetime.now())
        return await call_next(request)
