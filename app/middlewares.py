import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

from aws_lambda_powertools import Logger
from starlette import status
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app import Settings

X_CORRELATION_ID = "X-Correlation-ID"

correlation_id = ContextVar(X_CORRELATION_ID)
logger = Logger(utc=True)
settings = Settings()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id.set(
            request.headers[X_CORRELATION_ID]
            if request.headers.get(X_CORRELATION_ID)
            else str(uuid.uuid4())
        )
        logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    RATE_LIMIT_DURATION = timedelta(seconds=settings.rate_limit_duration_in_seconds)

    def __init__(self, app):
        super().__init__(app)
        self.clients = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if settings.rate_limiting:
            client_ip = request.client.host
            client = self.clients.get(
                client_ip, {"request_count": 0, "last_request": datetime.min}
            )
            if (datetime.now() - client["last_request"]) > self.RATE_LIMIT_DURATION:
                client["request_count"] = 1
            else:
                if client["request_count"] >= settings.rate_limit_requests:
                    logger.warning(
                        "The client has exceeded the rate limit and has been rate limited",
                        host=request.client.host,
                    )
                    return JSONResponse(
                        content={
                            "message": "Rate limit exceeded. Please try again later"
                        },
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        headers=self.__get_rate_limit_headers(client),
                    )
                client["request_count"] += 1
            client["last_request"] = datetime.now()
            self.clients[client_ip] = client
            response = await call_next(request)
            response.headers.update(self.__get_rate_limit_headers(client))
            return response
        else:
            logger.info("Rate limiting is turned off")
        return await call_next(request)

    def __get_rate_limit_headers(self, client: dict[str, Any]) -> dict[str, Any]:
        return {
            "X-RateLimit-Limit": str(settings.rate_limit_requests),
            "X-RateLimit-Remaining": str(
                settings.rate_limit_requests - client["request_count"]
            ),
            "X-RateLimit-Reset": str(
                int(
                    (
                        client["last_request"].replace(second=0, microsecond=0)
                        + timedelta(minutes=1)
                    ).timestamp()
                )
            ),
        }
