import uuid
from contextvars import ContextVar

from aws_lambda_powertools import Logger
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.services.rate_limiter_service import RateLimiterService, RateLimitResult
from app.settings import Settings

X_CORRELATION_ID = "X-Correlation-ID"

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger()
settings = Settings()


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
        if request.url.path == "/health":
            return await call_next(request)

        if settings.rate_limiting:
            client_ip = request.client.host if request.client else None
            if client_ip:
                result = self._rate_limiter.check_rate_limit(
                    client_ip, self._get_rate_limit_bucket(request)
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
    def _get_rate_limit_bucket(request: Request) -> str:
        route = request.scope.get("route")
        route_template = getattr(route, "path", None)
        if isinstance(route_template, str):
            return route_template

        parts = request.url.path.strip("/").split("/")
        if parts == ["api", "v1", "posts"]:
            return "/api/v1/posts"
        if parts == ["api", "v1", "posts", "archive"]:
            return "/api/v1/posts/archive"
        if len(parts) == 4 and parts[:3] == ["api", "v1", "posts"]:
            return "/api/v1/posts/{uuid}"
        if len(parts) == 5 and parts[:3] == ["api", "v1", "posts"]:
            if parts[4] == "publish":
                return "/api/v1/posts/{uuid}/publish"
            if parts[4] == "attachments":
                return "/api/v1/posts/{post_uuid}/attachments"
        if len(parts) == 6 and parts[:3] == ["api", "v1", "posts"]:
            if parts[4] == "attachments":
                return "/api/v1/posts/{post_uuid}/attachments/{attachment_uuid}"
        if len(parts) == 7 and parts[:3] == ["api", "v1", "posts"]:
            if parts[4] == "attachments" and parts[6] == "download":
                return (
                    "/api/v1/posts/{post_uuid}/attachments/{attachment_uuid}/download"
                )
            return "/api/v1/posts/{year}/{month}/{day}/{slug}"
        return "unmatched"

    @staticmethod
    def _get_rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_at),
        }
