"""
Pydantic schemas for the transaction submission/scoring pipeline and
transaction listing/detail views.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.fraud_log import LogStatus, PipelineStage
from app.models.fraud_prediction import Decision


class TransactionCreate(BaseModel):
    """POST /predict request body — a single transaction to score."""

    time_feature: float = Field(
        ..., ge=0, description="Seconds elapsed, matching the training dataset's Time column semantics"
    )
    amount: float = Field(..., gt=0)
    v_features: Dict[str, float] = Field(
        ..., description='PCA components, e.g. {"V1": -1.359, "V2": 0.44, ..., "V28": -0.021}'
    )
    currency: str = Field(default="INR", max_length=3)
    merchant: Optional[str] = Field(default=None, max_length=255)
    customer_reference: Optional[str] = Field(default=None, max_length=255)
    card_last4: Optional[str] = Field(default=None, max_length=4)
    device_info: Optional[str] = Field(default=None, max_length=255)
    ip_address: Optional[str] = Field(default=None, max_length=64)
    location: Optional[str] = Field(default=None, max_length=255)

    @field_validator("v_features")
    @classmethod
    def validate_v_features(cls, value: Dict[str, float]) -> Dict[str, float]:
        expected = {f"V{i}" for i in range(1, 29)}
        missing = expected - set(value.keys())
        if missing:
            raise ValueError(f"Missing required V-features: {sorted(missing)}")
        return value


class ShapFeatureOut(BaseModel):
    feature: str
    label: str
    impact: float
    value: float


class FraudPredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_fraud: bool
    fraud_probability: float
    risk_score: float
    confidence: float
    decision: Decision
    model_version: str
    latency_ms: float
    top_shap_features: List[ShapFeatureOut]
    explanation: str
    created_at: datetime


class FraudLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: PipelineStage
    status: LogStatus
    message: Optional[str] = None
    created_at: datetime


class TransactionOut(BaseModel):
    """Lightweight representation for list views — prediction summary flattened in."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: float
    currency: str
    merchant: Optional[str] = None
    customer_reference: Optional[str] = None
    created_at: datetime
    risk_score: Optional[float] = None
    decision: Optional[Decision] = None
    is_fraud: Optional[bool] = None

    @classmethod
    def from_transaction(cls, txn) -> "TransactionOut":
        """
        Builds this schema from a Transaction ORM instance, flattening in its
        (optionally absent) prediction. Deliberately explicit rather than
        relying on automatic from_attributes mapping, since risk_score/
        decision/is_fraud live on the related FraudPrediction, not on
        Transaction itself.
        """
        pred = txn.prediction
        return cls(
            id=txn.id,
            amount=txn.amount,
            currency=txn.currency,
            merchant=txn.merchant,
            customer_reference=txn.customer_reference,
            created_at=txn.created_at,
            risk_score=pred.risk_score if pred else None,
            decision=pred.decision if pred else None,
            is_fraud=pred.is_fraud if pred else None,
        )


class TransactionDetailOut(BaseModel):
    """Full detail view — everything the frontend's transaction drawer needs."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    time_feature: float
    amount: float
    currency: str
    v_features: Dict[str, float]
    merchant: Optional[str] = None
    customer_reference: Optional[str] = None
    card_last4: Optional[str] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime
    prediction: Optional[FraudPredictionOut] = None
    decision_history: List[FraudLogOut] = Field(default_factory=list)


class TransactionListResponse(BaseModel):
    items: List[TransactionOut]
    total: int
    page: int
    page_size: int
    total_pages: int
