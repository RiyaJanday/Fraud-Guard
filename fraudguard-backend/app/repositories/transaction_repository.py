"""
Raw database access for Transaction records, including the filtered/paginated
listing query used by GET /transactions. All WHERE/JOIN logic for that query
lives here — the service layer just passes filter values through.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager

from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        """Eagerly loads the related prediction so it's safe to access after this call
        without triggering a lazy-load (and possible DetachedInstanceError)."""
        stmt = (
            select(Transaction)
            .outerjoin(Transaction.prediction)
            .options(contains_eager(Transaction.prediction))
            .where(Transaction.id == transaction_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_paginated(
        self,
        page: int,
        page_size: int,
        decision: Optional[Decision] = None,
        min_risk: Optional[float] = None,
        max_risk: Optional[float] = None,
        merchant: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[Transaction], int]:
        stmt = (
            select(Transaction)
            .outerjoin(Transaction.prediction)
            .options(contains_eager(Transaction.prediction))
        )

        if decision is not None:
            stmt = stmt.where(FraudPrediction.decision == decision)
        if min_risk is not None:
            stmt = stmt.where(FraudPrediction.risk_score >= min_risk)
        if max_risk is not None:
            stmt = stmt.where(FraudPrediction.risk_score <= max_risk)
        if merchant:
            stmt = stmt.where(Transaction.merchant.ilike(f"%{merchant}%"))
        if date_from is not None:
            stmt = stmt.where(Transaction.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.created_at <= date_to)

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Transaction.id).subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.execute(stmt).unique().scalars().all())

        return items, total

    def list_recent_features(self, limit: int = 500) -> list[dict]:
        """
        Returns the most recent `limit` transactions' raw model-input
        features (V1..V28 + Amount) as plain dicts — used by drift_detector
        to compare live traffic against the training distribution. Deliberately
        selects only `v_features` and `amount` (not the full ORM object with
        its prediction join) since drift checking doesn't need anything else.
        """
        stmt = (
            select(Transaction.v_features, Transaction.amount)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [{**v_features, "Amount": amount} for v_features, amount in rows]
