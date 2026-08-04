"""Raw database access for FraudPrediction records."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.fraud_prediction import Decision, FraudPrediction


class FraudPredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, prediction: FraudPrediction) -> FraudPrediction:
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_by_transaction_id(self, transaction_id: uuid.UUID) -> Optional[FraudPrediction]:
        stmt = select(FraudPrediction).where(FraudPrediction.transaction_id == transaction_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_recent(self, limit: int = 200, high_risk_only: bool = False) -> list[FraudPrediction]:
        """
        Most recent predictions, transaction eager-loaded. Used two ways by
        ExplainabilityService: a large sample (high_risk_only=False) to
        compute genuine global feature importance across real traffic, and
        a small high_risk_only=True sample to show a few concrete example
        explanations — real SHAP output from real scored transactions, not
        fabricated walkthroughs.
        """
        stmt = select(FraudPrediction).options(joinedload(FraudPrediction.transaction))
        if high_risk_only:
            stmt = stmt.where(FraudPrediction.decision != Decision.APPROVE)
        stmt = stmt.order_by(FraudPrediction.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())
