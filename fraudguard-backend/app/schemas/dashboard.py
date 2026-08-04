"""
Pydantic schemas for the dashboard stats/charts and analytics endpoints.

Every number here comes from a real aggregate query over transactions,
predictions, and the active model's stored metrics — nothing is fabricated.
Where the frontend's mock data assumed things the schema doesn't actually
have (e.g. named fraud "types" like card-testing/account-takeover, which
this dataset has no way to distinguish), the shape is adapted to what's
honestly computable instead — decision breakdown (approve/mfa/blocked)
rather than invented fraud categories.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DashboardDeltas(BaseModel):
    """
    Week-over-week percent change for each headline stat. 0.0 when there
    isn't enough history yet (e.g. a brand-new deployment) rather than a
    fabricated number — an honest "not enough data" state is preferable to
    a fake trend arrow.
    """

    total_transactions: float = 0.0
    fraud_detected: float = 0.0
    fraud_blocked: float = 0.0
    detection_accuracy: float = 0.0
    avg_risk_score: float = 0.0


class DashboardStatsOut(BaseModel):
    total_transactions: int
    fraud_detected: int
    fraud_blocked: int
    detection_accuracy: float  # 0-100, from the active model's stored accuracy
    avg_risk_score: float  # 0-100
    deltas: DashboardDeltas


class VolumeSeriesOut(BaseModel):
    labels: List[str]
    legit: List[int]
    fraud: List[int]


class DecisionDistributionOut(BaseModel):
    labels: List[str]
    values: List[int]


class RiskTrendOut(BaseModel):
    labels: List[str]
    values: List[float]


class ModelPerformanceOut(BaseModel):
    labels: List[str]
    values: List[float]


class HeatmapRow(BaseModel):
    day: str
    values: List[int]


class DashboardChartsOut(BaseModel):
    volume: VolumeSeriesOut
    fraud_distribution: DecisionDistributionOut
    risk_trend: RiskTrendOut
    model_performance: ModelPerformanceOut
    heatmap: List[HeatmapRow]
    heatmap_hours: List[str]


class AlertOut(BaseModel):
    id: UUID
    title: str
    merchant: Optional[str] = None
    risk_score: float
    time: datetime
    severity: str  # "danger" (blocked) or "warning" (mfa_required)


class MerchantRiskOut(BaseModel):
    merchant: str
    flagged_count: int
    total_count: int


class CurrencyBreakdownOut(BaseModel):
    currency: str
    total_count: int
    flagged_count: int


class AnalyticsOut(BaseModel):
    volume: VolumeSeriesOut
    fraud_distribution: DecisionDistributionOut
    risk_trend: RiskTrendOut
    heatmap: List[HeatmapRow]
    heatmap_hours: List[str]
    top_merchants_by_risk: List[MerchantRiskOut]
    currency_breakdown: List[CurrencyBreakdownOut]
