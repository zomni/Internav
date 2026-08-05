import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.log.setup import set_trace_id


class TraceIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        trace_id = headers.get(b"x-trace-id", b"").decode()
        if not trace_id:
            trace_id = uuid4().hex[:16]
        set_trace_id(trace_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                headers.append("X-Trace-ID", trace_id)
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import logging

        logger = logging.getLogger("access")
        method = scope.get("method", "")
        path = scope.get("path", "")
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed = time.perf_counter() - start
                status = message["status"]
                logger.info(
                    "%s %s -> %d (%.1fms)",
                    method,
                    path,
                    status,
                    elapsed * 1000,
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)
