"""
Raw database access for FraudLog records — the per-transaction pipeline
event trail (Validation -> Preprocessing -> Prediction -> Decision ->
Persistence), surfaced to the frontend as "decision history".
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fraud_log import FraudLog, LogStatus, PipelineStage


class FraudLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        transaction_id: uuid.UUID,
        stage: PipelineStage,
        status: LogStatus,
        message: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> FraudLog:
        log = FraudLog(
            transaction_id=transaction_id, stage=stage, status=status, message=message, extra_data=extra_data
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_by_transaction(self, transaction_id: uuid.UUID) -> list[FraudLog]:
        stmt = (
            select(FraudLog)
            .where(FraudLog.transaction_id == transaction_id)
            .order_by(FraudLog.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
