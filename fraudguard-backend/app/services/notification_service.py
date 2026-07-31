"""
Creates Notification rows and pushes them live over WebSocket in the same
call — the two are intentionally coupled here rather than left for callers
to remember to do separately, since a notification that's persisted but
never broadcast (or broadcast but never persisted, so a refresh loses it)
would each be a subtly broken half of "real-time notifications".
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.websocket import manager
from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.notification import Notification, NotificationType
from app.models.transaction import Transaction
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationOut, NotificationWebSocketPayload


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.notifications = NotificationRepository(db)

    def create_and_broadcast(
        self,
        type: NotificationType,
        title: str,
        message: str,
        user_id: Optional[uuid.UUID] = None,
        related_transaction_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        notification = self.notifications.create(
            type=type,
            title=title,
            message=message,
            user_id=user_id,
            related_transaction_id=related_transaction_id,
        )
        payload = NotificationWebSocketPayload(notification=NotificationOut.model_validate(notification))
        manager.broadcast_sync(payload.model_dump(mode="json"))
        return notification

    def notify_for_prediction(self, transaction: Transaction, prediction: FraudPrediction) -> Optional[Notification]:
        """
        Called from TransactionService right after a prediction is
        persisted. Only BLOCKED and MFA_REQUIRED decisions generate a
        notification — a plain APPROVE on an ordinary transaction is the
        expected, silent, common case, and paging every analyst for every
        approved transaction would train them to ignore the panel entirely.
        """
        if prediction.decision == Decision.BLOCKED:
            return self.create_and_broadcast(
                type=NotificationType.BLOCKED_TRANSACTION,
                title="Transaction Blocked",
                message=(
                    f"Transaction {transaction.id} for {transaction.currency} {transaction.amount:,.2f} "
                    f"was blocked — risk score {prediction.risk_score:.1f}."
                ),
                related_transaction_id=transaction.id,
            )
        if prediction.decision == Decision.MFA_REQUIRED:
            return self.create_and_broadcast(
                type=NotificationType.HIGH_RISK_ALERT,
                title="High Risk Transaction",
                message=(
                    f"Transaction {transaction.id} for {transaction.currency} {transaction.amount:,.2f} "
                    f"flagged for MFA — risk score {prediction.risk_score:.1f}."
                ),
                related_transaction_id=transaction.id,
            )
        return None
