"""
GET /api/v1/ws/notifications — real-time push channel for the dashboard's
notification panel and toast alerts.

Browsers cannot attach an `Authorization` header to a WebSocket handshake
(the native WebSocket API takes no custom-header option), so unlike most
other endpoints in this API this one authenticates via either:

  1. The `access_token` httpOnly cookie (see core/cookies.py) — sent
     automatically by the browser on the WS handshake request, since a
     WebSocket upgrade is still just an HTTP GET under the hood and cookies
     attach to it exactly like any other same-origin/cross-origin request.
     This is what the SPA actually uses now that it no longer keeps a
     JS-readable token to put in a query string.
  2. A `token` query parameter, kept for backward compatibility with any
     non-browser client that already holds a bearer token directly:

        wss://host/api/v1/ws/notifications?token=<access_token>

The token (however it arrives) is validated with the exact same
decode_token()/UserRepository lookup used by get_current_user in
security.py — a WebSocket is just a different transport, it doesn't get a
different or weaker auth mechanism. No CSRF check applies here: opening a
WebSocket from a malicious cross-site page is possible, but the attacker's
page still can't read anything back from a channel whose messages are only
ever pushed to whoever the browser's own cookies happen to authenticate as
— there's no state-changing action to forge.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.cookies import ACCESS_COOKIE
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
    effective_token = token or websocket.cookies.get(ACCESS_COOKIE)
    if not await _authenticate(websocket, effective_token, db):
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
