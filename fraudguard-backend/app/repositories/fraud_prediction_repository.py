"""Raw database access for FraudPrediction records."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fraud_prediction import FraudPrediction


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
