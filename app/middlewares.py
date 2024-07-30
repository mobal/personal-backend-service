import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

import httpx
from aws_lambda_powertools import Logger
from fastapi import status
from httpx import HTTPError
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app import Settings

COUNTRY_IS_API_BASE_URL = "https://api.country.is"
X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger(utc=True)
settings = Settings()

banned_hosts: list[str] = []
clients: dict[str, Any] = {}


class ClientValidationMiddleware(BaseHTTPMiddleware):
    RESTRICTED_COUNTRY_CODES = ["CN", "RU"]

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else None
        if client_ip:
            if client_ip in banned_hosts:
                is_banned = True
            else:
                is_banned = await self.__validate_host(client_ip)
                if is_banned:
                    banned_hosts.append(client_ip)
            if is_banned:
                return JSONResponse(
                    content={"message": "Forbidden"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        return await call_next(request)

    async def __validate_host(self, client_ip: str) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{COUNTRY_IS_API_BASE_URL}/{client_ip}")
                response.raise_for_status()
                json_body = response.json()
                if json_body["country"] in self.RESTRICTED_COUNTRY_CODES:
                    logger.info(
                        f"Client has restricted country_code={json_body['country']} with {client_ip=}"
                    )
                    return True
            except HTTPError as exc:
                logger.warning(f"HTTP exception for {exc.request.url}")
        return False


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

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if settings.rate_limiting:
            client_ip = request.client.host if request.client else None
            if client_ip:
                client = clients.get(
                    client_ip, {"request_count": 0, "last_request": datetime.min}
                )
                if (datetime.now() - client["last_request"]) > self.RATE_LIMIT_DURATION:
                    client["request_count"] = 1
                else:
                    if client["request_count"] >= settings.rate_limit_requests:
                        logger.warning(
                            "The client has exceeded the rate limit and has been rate limited",
                            host=client_ip,
                        )
                        return JSONResponse(
                            content={
                                "message": "Rate limit exceeded. Please try again later"
                            },
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers=await self.__get_rate_limit_headers(client),
                        )
                    client["request_count"] += 1
                client["last_request"] = datetime.now()
                clients[client_ip] = client
                response = await call_next(request)
                response.headers.update(await self.__get_rate_limit_headers(client))
                return response
            else:
                logger.warning("Missing client information. Skipping rete limiting")
        else:
            logger.info("Rate limiting is turned off")
        return await call_next(request)

    async def __get_rate_limit_headers(self, client: dict[str, Any]) -> dict[str, Any]:
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
