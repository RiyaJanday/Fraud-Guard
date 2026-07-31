"""
REST fallback/history for notifications:

    GET   /notifications              — paginated list + unread count (panel's initial load)
    PATCH /notifications/{id}/read    — mark one as read
    PATCH /notifications/read-all     — mark everything read

The WebSocket channel (ws.py) handles live push; these endpoints handle the
"what did I miss while disconnected" case and the read/unread state, which a
push-only channel can't represent on its own.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationListResponse, NotificationOut

router = APIRouter()

_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get("", response_model=NotificationListResponse, summary="List notifications for the current user")
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> NotificationListResponse:
    repo = NotificationRepository(db)
    items, total = repo.list_for_user(current_user.id, page=page, page_size=page_size)
    unread_count = repo.count_unread_for_user(current_user.id)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return NotificationListResponse(
        items=[NotificationOut.model_validate(n) for n in items],
        unread_count=unread_count,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark a single notification as read",
    responses={404: {"description": "Notification not found."}},
)
def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> NotificationOut:
    repo = NotificationRepository(db)
    notification = repo.get_by_id(notification_id)
    if notification is None:
        raise NotFoundException(f"Notification {notification_id} was not found.")
    notification = repo.mark_read(notification)
    return NotificationOut.model_validate(notification)


@router.patch("/read-all", summary="Mark every notification visible to the current user as read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> dict:
    count = NotificationRepository(db).mark_all_read_for_user(current_user.id)
    return {"marked_read": count}
