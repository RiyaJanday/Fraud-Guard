"""Pydantic schemas for the drift-detection endpoint."""

from typing import List, Optional

from pydantic import BaseModel


class DriftFeatureOut(BaseModel):
    feature: str
    ks_statistic: float
    p_value: float
    drifted: bool


class DriftReportOut(BaseModel):
    status: str  # "ok" | "insufficient_data"
    sample_size: int
    minimum_required: Optional[int] = None
    message: Optional[str] = None
    features: List[DriftFeatureOut]
    drift_detected: bool
    drifted_feature_count: int
    total_feature_count: int
    drift_ratio: float
    threshold: float
