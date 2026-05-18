from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request id to each request and expose it via logs and response headers."""

    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(self.header_name) or uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[self.header_name] = rid
        return response
