"""Pydantic schemas for the notifications panel and the WebSocket push payload."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    related_transaction_id: Optional[uuid.UUID] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationOut]
    unread_count: int
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationWebSocketPayload(BaseModel):
    """
    Shape pushed down the WebSocket, distinct from NotificationOut: the
    frontend needs `event` to distinguish a brand-new notification arriving
    live from other future event types on the same channel (e.g. a future
    "transaction_updated" push), without needing a second WebSocket endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    event: str = "notification"
    notification: NotificationOut
