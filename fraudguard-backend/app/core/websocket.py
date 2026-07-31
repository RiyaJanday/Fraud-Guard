"""
In-memory WebSocket connection registry for the /ws/notifications channel.

The rest of the application is entirely synchronous — SQLAlchemy's `Session`,
not `AsyncSession`, and route handlers declared with `def`, not `async def`
(see prediction.py). FastAPI runs `def` handlers in a worker thread pool,
not on the main asyncio event loop, so a plain `await manager.broadcast(...)`
call from inside transaction_service is unreachable from there — there is no
event loop running on that thread to await into.

ConnectionManager solves this by capturing a reference to the *main* event
loop at startup (see app.main's lifespan, which runs ON that loop) and using
`asyncio.run_coroutine_threadsafe` to hand the broadcast coroutine to it from
whatever worker thread called `broadcast_sync`. This is the standard pattern
for bridging a sync codebase into an async WebSocket layer without rewriting
the whole app to async SQLAlchemy — which is out of scope for this project.
"""

import asyncio
import json
from typing import Any, Optional

from fastapi import WebSocket

from app.core.logging import logger


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once from app.main's lifespan, on the main event loop."""
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("WebSocket connected | total_connections={}", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info("WebSocket disconnected | total_connections={}", len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Sends `payload` (as JSON) to every currently-connected client."""
        if not self._connections:
            return
        message = json.dumps(payload, default=str)
        dead: set[WebSocket] = set()
        for connection in list(self._connections):
            try:
                await connection.send_text(message)
            except Exception:  # noqa: BLE001 — one broken socket must not break the broadcast to everyone else
                dead.add(connection)
        self._connections -= dead

    def broadcast_sync(self, payload: dict[str, Any]) -> None:
        """
        Thread-safe entry point for sync callers — i.e. services invoked from
        a FastAPI `def` route handler running in the threadpool, which is
        every write path in this app (submit_transaction, review decisions).

        Silently no-ops (with a log line) if called before the event loop is
        bound, e.g. in a unit test that constructs a service directly without
        booting the full app — that should never crash the caller's actual
        business logic just because nobody is listening for a broadcast yet.
        """
        if self._loop is None:
            logger.warning("WebSocket broadcast skipped — event loop not bound yet.")
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)


# Module-level singleton — mirrors the pattern of get_redis_client() being a
# single shared client rather than one per request.
manager = ConnectionManager()
