import logging

from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

BODY_TOO_LARGE_ERROR_TEMPLATE = "El cuerpo de la petición supera el máximo permitido de {max_size} bytes."


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        detail = BODY_TOO_LARGE_ERROR_TEMPLATE.format(max_size=self.max_body_bytes)
        if _declared_length(scope) > self.max_body_bytes:
            logger.warning("Rejected request: declared body exceeds max_size=%d", self.max_body_bytes)
            await JSONResponse({"detail": detail}, status_code=413)(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_body_bytes:
                logger.warning("Rejected request: streamed body exceeds max_size=%d", self.max_body_bytes)
                raise HTTPException(status_code=413, detail=detail)
            return message

        await self.app(scope, limited_receive, send)


def _declared_length(scope: Scope) -> int:
    for name, value in scope["headers"]:
        if name == b"content-length" and value.isdigit():
            return int(value)
    return 0
