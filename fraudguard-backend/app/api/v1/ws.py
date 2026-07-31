"""
GET /api/v1/ws/notifications — real-time push channel for the dashboard's
notification panel and toast alerts.

Browsers cannot attach an `Authorization` header to a WebSocket handshake
(the native WebSocket API takes no custom-header option), so unlike every
other endpoint in this API — which authenticates via a Bearer token through
HTTPBearer — this one authenticates via a `token` query parameter instead:

    wss://host/api/v1/ws/notifications?token=<access_token>

The token is validated with the exact same decode_token()/UserRepository
lookup used by get_current_user in security.py — a WebSocket is just a
different transport, it doesn't get a different or weaker auth mechanism.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import TokenType, decode_token
from app.core.websocket import manager
from app.database.session import get_db
from app.repositories.user_repository import UserRepository

router = APIRouter()
settings = get_settings()


async def _authenticate(websocket: WebSocket, token: Optional[str], db: Session) -> bool:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return False

    try:
        payload = decode_token(token, settings.SECRET_KEY, TokenType.ACCESS)
        user_id = uuid.UUID(payload["sub"])
    except Exception:  # noqa: BLE001 — any decode/format failure is just "not authenticated"
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return False

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or deactivated user")
        return False

    return True


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> None:
    if not await _authenticate(websocket, token, db):
        return

    await manager.connect(websocket)
    try:
        while True:
            # The client never needs to send anything — this is a
            # server-push-only channel. We still need an active receive
            # loop so FastAPI/Starlette detects a client disconnect
            # promptly instead of leaving a dead socket registered.
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected normally.")
    finally:
        manager.disconnect(websocket)
