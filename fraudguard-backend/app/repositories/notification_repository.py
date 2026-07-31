"""Raw database access for Notification records."""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        type: NotificationType,
        title: str,
        message: str,
        user_id: Optional[uuid.UUID] = None,
        related_transaction_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            related_transaction_id=related_transaction_id,
            type=type,
            title=title,
            message=message,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_for_user(
        self, user_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Notification], int]:
        """
        Returns notifications addressed to `user_id` specifically, PLUS
        broadcasts (user_id IS NULL) — matching Notification's own docstring
        that a NULL user_id means "visible to every analyst/admin".
        """
        base_filter = or_(Notification.user_id == user_id, Notification.user_id.is_(None))

        total = self.db.execute(
            select(func.count()).select_from(Notification).where(base_filter)
        ).scalar_one()

        stmt = (
            select(Notification)
            .where(base_filter)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def count_unread_for_user(self, user_id: uuid.UUID) -> int:
        base_filter = or_(Notification.user_id == user_id, Notification.user_id.is_(None))
        stmt = select(func.count()).select_from(Notification).where(base_filter, Notification.is_read.is_(False))
        return self.db.execute(stmt).scalar_one()

    def get_by_id(self, notification_id: uuid.UUID) -> Optional[Notification]:
        return self.db.get(Notification, notification_id)

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read_for_user(self, user_id: uuid.UUID) -> int:
        base_filter = or_(Notification.user_id == user_id, Notification.user_id.is_(None))
        stmt = select(Notification).where(base_filter, Notification.is_read.is_(False))
        unread = list(self.db.execute(stmt).scalars().all())
        for notification in unread:
            notification.is_read = True
        self.db.commit()
        return len(unread)
