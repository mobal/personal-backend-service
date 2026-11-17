import re
import uuid
from contextvars import ContextVar

from aws_lambda_powertools import Logger
from fastapi.requests import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

X_CORRELATION_ID = "X-Correlation-ID"
CORRELATION_ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")

correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        x_correlation_id = request.headers.get(X_CORRELATION_ID)
        # The value is copied into every log line and the response, so only
        # accept short identifier-like values from the client.
        if not x_correlation_id or not CORRELATION_ID_RE.fullmatch(x_correlation_id):
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
