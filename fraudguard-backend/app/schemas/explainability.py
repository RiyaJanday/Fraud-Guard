"""Pydantic schemas for the global model-explainability endpoint."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.fraud_prediction import Decision
from app.schemas.transaction import ShapFeatureOut


class ConfusionMatrixOut(BaseModel):
    tp: int
    fp: int
    tn: int
    fn: int


class ModelInfoOut(BaseModel):
    version: str
    algorithm: str
    status: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    training_date: Optional[datetime] = None
    dataset_name: str
    dataset_row_count: Optional[int] = None
    confusion_matrix: Optional[ConfusionMatrixOut] = None


class FeatureImportanceOut(BaseModel):
    feature: str
    label: str
    avg_impact: float
    sample_count: int


class RecentExplanationOut(BaseModel):
    transaction_id: UUID
    merchant: Optional[str] = None
    amount: float
    currency: str
    risk_score: float
    decision: Decision
    explanation: str
    top_shap_features: List[ShapFeatureOut]
    created_at: datetime


class ExplainabilityOut(BaseModel):
    model: Optional[ModelInfoOut] = None
    global_feature_importance: List[FeatureImportanceOut]
    recent_explanations: List[RecentExplanationOut]
    sample_size: int
