"""
Business logic for the dashboard/analytics endpoints. Deliberately thin —
almost all the real work is aggregate SQL in AnalyticsRepository; this layer
mostly assembles repository results into response schemas and pulls in the
active model's stored metrics for detection_accuracy / model_performance.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.dashboard import (
    AlertOut,
    AnalyticsOut,
    DashboardChartsOut,
    DashboardDeltas,
    DashboardStatsOut,
    DecisionDistributionOut,
    HeatmapRow,
    MerchantRiskOut,
    ModelPerformanceOut,
    RiskTrendOut,
    VolumeSeriesOut,
)


def _pct_change(current: float, previous: float) -> float:
    """Week-over-week percent change. Returns 0.0 (not a divide-by-zero crash,
    and not a misleading +/-infinity) when there's no prior-period baseline yet."""
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.analytics = AnalyticsRepository(db)
        self.model_registry = ModelRegistryRepository(db)

    # ------------------------------------------------------------------ #
    def get_dashboard_stats(self) -> DashboardStatsOut:
        now = datetime.now(timezone.utc)
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)

        total = self.analytics.count_transactions()
        fraud = self.analytics.count_fraud()
        blocked = self.analytics.count_blocked()
        avg_risk = self.analytics.avg_risk_score()

        active_model = self.model_registry.get_active()
        accuracy = round((active_model.accuracy or 0.0) * 100, 2) if active_model else 0.0

        # This-week vs last-week deltas for a "vs last week" indicator that's
        # real, not decorative — even if most demo data lands in one bucket
        # and the delta comes out as 0.0, that's an honest reflection of the
        # available history rather than a fabricated trend.
        total_this_week = self.analytics.count_transactions(since=this_week_start)
        total_last_week = self.analytics.count_transactions(since=last_week_start) - total_this_week
        fraud_this_week = self.analytics.count_fraud(since=this_week_start)
        fraud_last_week = self.analytics.count_fraud(since=last_week_start) - fraud_this_week
        blocked_this_week = self.analytics.count_blocked(since=this_week_start)
        blocked_last_week = self.analytics.count_blocked(since=last_week_start) - blocked_this_week
        risk_this_week = self.analytics.avg_risk_score(since=this_week_start)
        risk_last_week = self.analytics.avg_risk_score(since=last_week_start)

        deltas = DashboardDeltas(
            total_transactions=_pct_change(total_this_week, total_last_week),
            fraud_detected=_pct_change(fraud_this_week, fraud_last_week),
            fraud_blocked=_pct_change(blocked_this_week, blocked_last_week),
            detection_accuracy=0.0,  # accuracy is a model property, not a weekly-moving stat
            avg_risk_score=_pct_change(risk_this_week, risk_last_week),
        )

        return DashboardStatsOut(
            total_transactions=total,
            fraud_detected=fraud,
            fraud_blocked=blocked,
            detection_accuracy=accuracy,
            avg_risk_score=round(avg_risk, 2),
            deltas=deltas,
        )

    # ------------------------------------------------------------------ #
    def get_dashboard_charts(self) -> DashboardChartsOut:
        volume = self.analytics.volume_by_hour(hours=24)
        distribution = self.analytics.decision_distribution()
        trend = self.analytics.risk_trend_by_day(days=14)
        heatmap = self.analytics.heatmap_by_day_hour()

        active_model = self.model_registry.get_active()
        if active_model:
            model_performance = {
                "labels": ["Precision", "Recall", "F1 Score", "ROC-AUC", "PR-AUC", "Accuracy"],
                "values": [
                    round((active_model.precision or 0) * 100, 1),
                    round((active_model.recall or 0) * 100, 1),
                    round((active_model.f1_score or 0) * 100, 1),
                    round((active_model.roc_auc or 0) * 100, 1),
                    round((active_model.pr_auc or 0) * 100, 1),
                    round((active_model.accuracy or 0) * 100, 1),
                ],
            }
        else:
            model_performance = {
                "labels": ["Precision", "Recall", "F1 Score", "ROC-AUC", "PR-AUC", "Accuracy"],
                "values": [0, 0, 0, 0, 0, 0],
            }

        return DashboardChartsOut(
            volume=VolumeSeriesOut(**volume),
            fraud_distribution=DecisionDistributionOut(**distribution),
            risk_trend=RiskTrendOut(**trend),
            model_performance=ModelPerformanceOut(**model_performance),
            heatmap=[HeatmapRow(**row) for row in heatmap["rows"]],
            heatmap_hours=heatmap["hours"],
        )

    # ------------------------------------------------------------------ #
    def get_analytics(self) -> AnalyticsOut:
        volume = self.analytics.volume_by_hour(hours=24)
        distribution = self.analytics.decision_distribution()
        trend = self.analytics.risk_trend_by_day(days=14)
        heatmap = self.analytics.heatmap_by_day_hour()
        top_merchants = self.analytics.top_merchants_by_risk()

        return AnalyticsOut(
            volume=VolumeSeriesOut(**volume),
            fraud_distribution=DecisionDistributionOut(**distribution),
            risk_trend=RiskTrendOut(**trend),
            heatmap=[HeatmapRow(**row) for row in heatmap["rows"]],
            heatmap_hours=heatmap["hours"],
            top_merchants_by_risk=[MerchantRiskOut(**m) for m in top_merchants],
        )

    # ------------------------------------------------------------------ #
    def get_recent_alerts(self, limit: int = 5) -> list[AlertOut]:
        predictions = self.analytics.recent_alerts(limit=limit)
        alerts = []
        for pred in predictions:
            txn = pred.transaction
            title = (
                "Transaction blocked automatically"
                if pred.decision.value == "blocked"
                else "Step-up verification required"
            )
            severity = "danger" if pred.decision.value == "blocked" else "warning"
            alerts.append(
                AlertOut(
                    id=pred.id,
                    title=title,
                    merchant=txn.merchant if txn else None,
                    risk_score=pred.risk_score,
                    time=pred.created_at,
                    severity=severity,
                )
            )
        return alerts
