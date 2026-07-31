"""
Raw aggregate database queries backing the dashboard/analytics endpoints.
All time-bucketing uses Postgres's date_trunc, since this project targets
Postgres exclusively (no cross-database portability concerns here).

Every "series" query zero-fills its full label range (e.g. all 24 hours,
all 14 days, all 7 weekdays) rather than only returning buckets that
happen to have data — a demo with only a handful of real transactions
should still render a properly-shaped chart, not a chart with 2 points.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.transaction import Transaction


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Headline stats
    # ------------------------------------------------------------------ #
    def count_transactions(self, since: Optional[datetime] = None) -> int:
        stmt = select(func.count()).select_from(Transaction)
        if since is not None:
            stmt = stmt.where(Transaction.created_at >= since)
        return self.db.execute(stmt).scalar_one()

    def count_fraud(self, since: Optional[datetime] = None) -> int:
        stmt = select(func.count()).select_from(FraudPrediction).where(FraudPrediction.is_fraud.is_(True))
        if since is not None:
            stmt = stmt.where(FraudPrediction.created_at >= since)
        return self.db.execute(stmt).scalar_one()

    def count_blocked(self, since: Optional[datetime] = None) -> int:
        stmt = select(func.count()).select_from(FraudPrediction).where(FraudPrediction.decision == Decision.BLOCKED)
        if since is not None:
            stmt = stmt.where(FraudPrediction.created_at >= since)
        return self.db.execute(stmt).scalar_one()

    def avg_risk_score(self, since: Optional[datetime] = None) -> float:
        stmt = select(func.avg(FraudPrediction.risk_score))
        if since is not None:
            stmt = stmt.where(FraudPrediction.created_at >= since)
        result = self.db.execute(stmt).scalar_one()
        return float(result) if result is not None else 0.0

    # ------------------------------------------------------------------ #
    # Charts
    # ------------------------------------------------------------------ #
    def volume_by_hour(self, hours: int = 24) -> dict[str, list]:
        # Bucket boundaries are computed from the CURRENT hour backward, not
        # forward from `now - hours` — the latter is an off-by-one trap: a
        # loop counting forward from (now - 24h) only reaches (now - 1h),
        # never including the current hour's own bucket, so anything
        # submitted "just now" silently falls outside every labeled bucket.
        now = datetime.now(timezone.utc)
        now_hour = now.replace(minute=0, second=0, microsecond=0)
        start_hour = now_hour - timedelta(hours=hours - 1)

        stmt = (
            select(
                func.date_trunc("hour", Transaction.created_at).label("bucket"),
                func.count(case((FraudPrediction.is_fraud.is_(False), 1))).label("legit"),
                func.count(case((FraudPrediction.is_fraud.is_(True), 1))).label("fraud"),
            )
            .select_from(Transaction)
            .outerjoin(Transaction.prediction)
            .where(Transaction.created_at >= start_hour)
            .group_by("bucket")
        )
        rows = {row.bucket: row for row in self.db.execute(stmt).all()}

        labels, legit, fraud = [], [], []
        for i in range(hours):
            bucket_time = start_hour + timedelta(hours=i)
            labels.append(bucket_time.strftime("%H:00"))
            row = rows.get(bucket_time)
            legit.append(row.legit if row else 0)
            fraud.append(row.fraud if row else 0)
        return {"labels": labels, "legit": legit, "fraud": fraud}

    def decision_distribution(self, since: Optional[datetime] = None) -> dict[str, list]:
        stmt = select(FraudPrediction.decision, func.count()).group_by(FraudPrediction.decision)
        if since is not None:
            stmt = stmt.where(FraudPrediction.created_at >= since)
        counts = {row[0]: row[1] for row in self.db.execute(stmt).all()}

        order = [Decision.APPROVE, Decision.MFA_REQUIRED, Decision.BLOCKED]
        label_map = {Decision.APPROVE: "Approved", Decision.MFA_REQUIRED: "MFA Required", Decision.BLOCKED: "Blocked"}
        return {
            "labels": [label_map[d] for d in order],
            "values": [counts.get(d, 0) for d in order],
        }

    def risk_trend_by_day(self, days: int = 14) -> dict[str, list]:
        # Same off-by-one fix as volume_by_hour: bucket backward from today,
        # not forward from (now - days), or today's own bucket never appears.
        now = datetime.now(timezone.utc)
        now_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_day = now_day - timedelta(days=days - 1)

        stmt = (
            select(
                func.date_trunc("day", FraudPrediction.created_at).label("bucket"),
                func.avg(FraudPrediction.risk_score).label("avg_risk"),
            )
            .where(FraudPrediction.created_at >= start_day)
            .group_by("bucket")
        )
        rows = {row.bucket: row.avg_risk for row in self.db.execute(stmt).all()}

        labels, values = [], []
        for i in range(days):
            day = start_day + timedelta(days=i)
            labels.append(day.strftime("%b %d"))
            avg = rows.get(day)
            values.append(round(float(avg), 2) if avg is not None else 0.0)
        return {"labels": labels, "values": values}

    def heatmap_by_day_hour(self) -> dict:
        """Fraud (is_fraud=True) event counts by weekday x 4-hour block, over all history."""
        stmt = (
            select(
                func.extract("dow", FraudPrediction.created_at).label("dow"),  # 0=Sunday..6=Saturday
                func.extract("hour", FraudPrediction.created_at).label("hour"),
                func.count(),
            )
            .where(FraudPrediction.is_fraud.is_(True))
            .group_by("dow", "hour")
        )
        rows = self.db.execute(stmt).all()

        # Bucket into 6 four-hour blocks per day, Monday-first to match the frontend.
        counts = {(int(dow), int(hour)): count for dow, hour, count in rows}
        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        # Postgres dow: 0=Sunday..6=Saturday -> remap to Monday-first index.
        pg_dow_to_label_index = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 0: 6}
        hour_blocks = [0, 4, 8, 12, 16, 20]

        grid = [[0] * len(hour_blocks) for _ in day_labels]
        for (dow, hour), count in counts.items():
            label_index = pg_dow_to_label_index.get(dow)
            if label_index is None:
                continue
            block_index = min(hour // 4, len(hour_blocks) - 1)
            grid[label_index][block_index] += count

        return {
            "rows": [{"day": day_labels[i], "values": grid[i]} for i in range(len(day_labels))],
            "hours": [f"{h:02d}:00" for h in hour_blocks],
        }

    # ------------------------------------------------------------------ #
    # Analytics extras
    # ------------------------------------------------------------------ #
    def top_merchants_by_risk(self, limit: int = 5) -> list[dict]:
        stmt = (
            select(
                Transaction.merchant,
                func.count().label("total"),
                func.count(case((FraudPrediction.decision != Decision.APPROVE, 1))).label("flagged"),
            )
            .select_from(Transaction)
            .outerjoin(Transaction.prediction)
            .where(Transaction.merchant.is_not(None))
            .group_by(Transaction.merchant)
            .order_by(func.count(case((FraudPrediction.decision != Decision.APPROVE, 1))).desc())
            .limit(limit)
        )
        return [
            {"merchant": row.merchant, "flagged_count": row.flagged, "total_count": row.total}
            for row in self.db.execute(stmt).all()
        ]

    def recent_alerts(self, limit: int = 5) -> list[FraudPrediction]:
        stmt = (
            select(FraudPrediction)
            .where(FraudPrediction.decision != Decision.APPROVE)
            .order_by(FraudPrediction.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
