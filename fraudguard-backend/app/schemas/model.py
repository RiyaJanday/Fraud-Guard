"""Pydantic schemas for GET /model/status and POST /model/retrain."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ActiveModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: str
    algorithm: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    pr_auc: float
    training_date: datetime
    dataset_row_count: int


class ModelStatusOut(BaseModel):
    active_model: Optional[ActiveModelOut] = None
    training_in_progress: bool
    training_started_at: Optional[str] = None
    training_finished_at: Optional[str] = None
    last_training_error: Optional[str] = None


class RetrainTriggerResponse(BaseModel):
    message: str
    training_in_progress: bool
