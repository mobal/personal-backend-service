import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

import httpx
import pendulum
from aws_lambda_powertools import Logger
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from httpx import HTTPError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app import Settings

COUNTRY_CACHE_TTL = timedelta(hours=1)
COUNTRY_IS_API_BASE_URL = "https://api.country.is"
X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger()
settings = Settings()

banned_hosts: list[str] = []
clients: dict[str, Any] = {}
country_cache: dict[str, tuple[bool, datetime]] = {}


class ClientValidationMiddleware(BaseHTTPMiddleware):
    RESTRICTED_COUNTRY_CODES = ["CN", "RU"]
    WHITELIST = ["127.0.0.1", "localhost", "::1"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if (
            not request.client
            or not request.client.host
            or request.client.host in self.WHITELIST
        ):
            return await call_next(request)
        client_ip = request.client.host
        is_banned = client_ip in banned_hosts or await self._is_banned_client_ip(
            client_ip
        )
        if is_banned:
            if client_ip not in banned_hosts:
                banned_hosts.append(client_ip)
            return JSONResponse(
                content={"message": "Forbidden"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)

    async def _is_banned_client_ip(self, client_ip: str) -> bool:
        if client_ip in country_cache:
            cached_is_banned, cached_time = country_cache[client_ip]
            if (pendulum.now() - cached_time) < COUNTRY_CACHE_TTL:
                logger.debug(f"Using cached country check result for {client_ip}")
                return cached_is_banned

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(
                    f"{COUNTRY_IS_API_BASE_URL}/{client_ip}",
                    timeout=5.0,
                )
                response.raise_for_status()
                country_code = response.json()["country"]
                if country_code in self.RESTRICTED_COUNTRY_CODES:
                    logger.info(
                        f"Client has restricted "
                        f"country_code={country_code} with {client_ip=}"
                    )
                    country_cache[client_ip] = (True, pendulum.now())
                    return True
                else:
                    country_cache[client_ip] = (False, pendulum.now())
                    return False
            except HTTPError as exc:
                logger.warning(f"HTTP exception for {exc.request.url}")
            except KeyError:
                logger.warning(
                    f"Unexpected response format from country.is API for {client_ip}"
                )
        return False


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id.set(
            request.headers.get(X_CORRELATION_ID)
            or request.scope.get("aws.context", {}).aws_request_id
            if request.scope.get("aws.context")
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
                rate_limited_response = self._check_rate_limit(client_ip)
                if rate_limited_response:
                    return rate_limited_response
                response = await call_next(request)
                response.headers.update(
                    self._get_rate_limit_headers(clients[client_ip])
                )
                return response
            else:
                logger.warning("Missing client information. Skipping rate limiting")
        else:
            logger.info("Rate limiting is turned off")
        return await call_next(request)

    def _check_rate_limit(self, client_ip: str) -> JSONResponse | None:
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
                    content={"message": "Rate limit exceeded. Please try again later"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers=self._get_rate_limit_headers(client),
                )
            client["request_count"] += 1
        client["last_request"] = datetime.now()
        clients[client_ip] = client
        return None

    def _get_rate_limit_headers(self, client: dict[str, Any]) -> dict[str, Any]:
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
