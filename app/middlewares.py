import uuid
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta

import httpx2
from aws_lambda_powertools import Logger
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from httpx2 import HTTPError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.services.rate_limiter_service import RateLimiterService, RateLimitResult
from app.settings import Settings

COUNTRY_CACHE_TTL = timedelta(hours=1)
COUNTRY_IS_API_BASE_URL = "https://api.country.is"
X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger()
settings = Settings()

banned_hosts: list[str] = []
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
            from app.api_handler import ErrorResponse

            if client_ip not in banned_hosts:
                banned_hosts.append(client_ip)
            return JSONResponse(
                content=jsonable_encoder(
                    ErrorResponse(
                        status=status.HTTP_403_FORBIDDEN,
                        id=str(uuid.uuid4()),
                        message="Forbidden",
                    )
                ),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)

    async def _is_banned_client_ip(self, client_ip: str) -> bool:
        if client_ip in country_cache:
            cached_is_banned, cached_time = country_cache[client_ip]
            if (datetime.now(UTC) - cached_time) < COUNTRY_CACHE_TTL:
                logger.debug(f"Using cached country check result for {client_ip}")
                return cached_is_banned

        async with httpx2.AsyncClient(timeout=5.0) as client:
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
                    country_cache[client_ip] = (True, datetime.now(UTC))
                    return True
                else:
                    country_cache[client_ip] = (False, datetime.now(UTC))
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
        x_correlation_id = request.headers.get(X_CORRELATION_ID)
        if not x_correlation_id:
            aws_context = request.scope.get("aws.context")
            if aws_context:
                x_correlation_id = aws_context.aws_request_id
            else:
                x_correlation_id = str(uuid.uuid4())

        correlation_id.set(x_correlation_id)
        logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, rate_limiter_service: RateLimiterService):
        super().__init__(app)
        self._rate_limiter = rate_limiter_service

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if settings.rate_limiting:
            client_ip = request.client.host if request.client else None
            if client_ip:
                result = self._rate_limiter.check_rate_limit(
                    client_ip, request.url.path
                )
                if not result.allowed:
                    return JSONResponse(
                        content={
                            "message": "Rate limit exceeded. Please try again later"
                        },
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        headers=self._get_rate_limit_headers(result),
                    )
                response = await call_next(request)
                response.headers.update(self._get_rate_limit_headers(result))
                return response
            else:
                logger.warning("Missing client information. Skipping rate limiting")
        else:
            logger.info("Rate limiting is turned off")
        return await call_next(request)

    @staticmethod
    def _get_rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_at),
        }
