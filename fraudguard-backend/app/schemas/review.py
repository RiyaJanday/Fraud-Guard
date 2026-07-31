"""
Pydantic schemas for the manual review workflow:

    Prediction -> (high risk) -> Manual Review Queue -> Analyst Decision
    (fraud/legitimate) -> ground truth stored for future retraining.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.fraud_prediction import Decision
from app.models.review import AnalystDecision, ReviewStatus
from app.schemas.transaction import ShapFeatureOut


class ReviewQueueOut(BaseModel):
    """Summary shown in the review queue list — enough to triage without opening each one."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fraud_prediction_id: uuid.UUID
    status: ReviewStatus
    assigned_analyst_id: Optional[uuid.UUID] = None
    assigned_analyst_name: Optional[str] = None
    analyst_decision: Optional[AnalystDecision] = None
    notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    # Denormalized transaction/prediction summary — avoids a second round
    # trip from the frontend just to show what's actually being reviewed.
    transaction_id: uuid.UUID
    amount: float
    merchant: Optional[str] = None
    risk_score: float
    fraud_probability: float
    decision: Decision
    explanation: str


class ReviewQueueDetailOut(ReviewQueueOut):
    """Full detail — everything an analyst needs to make the fraud/legitimate call."""

    top_shap_features: List[ShapFeatureOut]
    v_features: Dict[str, float]
    time_feature: float
    currency: str


class ReviewResolveRequest(BaseModel):
    """POST /review-queue/{id}/resolve request body."""

    decision: AnalystDecision
    notes: Optional[str] = Field(default=None, max_length=2000)


class ReviewListResponse(BaseModel):
    items: List[ReviewQueueOut]
    total: int
    page: int
    page_size: int
    total_pages: int
