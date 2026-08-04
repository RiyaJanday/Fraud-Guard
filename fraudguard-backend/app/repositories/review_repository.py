"""
Raw database access for ReviewQueue records. Eager-loads the related
FraudPrediction -> Transaction chain and the assigned analyst, since every
read path needs that denormalized summary data (see ReviewService._to_out).
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.fraud_prediction import FraudPrediction
from app.models.review import ReviewQueue, ReviewStatus

# Every read query needs the same eager-load chain — defined once, reused everywhere.
_EAGER_LOAD = (
    joinedload(ReviewQueue.fraud_prediction).joinedload(FraudPrediction.transaction),
    joinedload(ReviewQueue.analyst),
)


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, fraud_prediction_id: uuid.UUID) -> ReviewQueue:
        review = ReviewQueue(fraud_prediction_id=fraud_prediction_id, status=ReviewStatus.PENDING)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return self.get_by_id(review.id)  # re-fetch with eager-loaded relationships

    def get_by_id(self, review_id: uuid.UUID) -> Optional[ReviewQueue]:
        stmt = select(ReviewQueue).options(*_EAGER_LOAD).where(ReviewQueue.id == review_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_prediction_id(self, prediction_id: uuid.UUID) -> Optional[ReviewQueue]:
        stmt = select(ReviewQueue).options(*_EAGER_LOAD).where(ReviewQueue.fraud_prediction_id == prediction_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_paginated(
        self, page: int, page_size: int, status: Optional[ReviewStatus] = None
    ) -> tuple[list[ReviewQueue], int]:
        stmt = select(ReviewQueue).options(*_EAGER_LOAD)
        if status is not None:
            stmt = stmt.where(ReviewQueue.status == status)

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(ReviewQueue.id).subquery())
        total = self.db.execute(count_stmt).scalar_one()

        # Oldest first — a review queue is processed FIFO, not newest-first
        # like the transaction list (which is browsed, not worked through).
        stmt = stmt.order_by(ReviewQueue.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def save(self, review: ReviewQueue) -> ReviewQueue:
        self.db.commit()
        self.db.refresh(review)
        return self.get_by_id(review.id)

    def get_stats_for_analyst(self, analyst_id: uuid.UUID) -> dict:
        """
        Real per-analyst metrics for the Profile page — counts and average
        response time, computed directly from resolved reviews assigned to
        this analyst. No fabricated "accuracy" figure: that would need
        ground truth this system doesn't independently have.
        """
        from app.models.review import AnalystDecision  # local import avoids a circular import at module load

        base = select(ReviewQueue).where(
            ReviewQueue.assigned_analyst_id == analyst_id, ReviewQueue.status == ReviewStatus.RESOLVED
        )
        cases_reviewed = self.db.execute(
            select(func.count()).select_from(base.with_only_columns(ReviewQueue.id).subquery())
        ).scalar_one()

        fraud_confirmed = self.db.execute(
            select(func.count()).select_from(
                base.where(ReviewQueue.analyst_decision == AnalystDecision.FRAUD)
                .with_only_columns(ReviewQueue.id)
                .subquery()
            )
        ).scalar_one()

        marked_legitimate = self.db.execute(
            select(func.count()).select_from(
                base.where(ReviewQueue.analyst_decision == AnalystDecision.LEGITIMATE)
                .with_only_columns(ReviewQueue.id)
                .subquery()
            )
        ).scalar_one()

        avg_seconds = self.db.execute(
            select(func.avg(func.extract("epoch", ReviewQueue.resolved_at - ReviewQueue.created_at))).where(
                ReviewQueue.assigned_analyst_id == analyst_id,
                ReviewQueue.status == ReviewStatus.RESOLVED,
                ReviewQueue.resolved_at.is_not(None),
            )
        ).scalar_one()

        return {
            "cases_reviewed": cases_reviewed,
            "fraud_confirmed": fraud_confirmed,
            "marked_legitimate": marked_legitimate,
            "avg_response_minutes": round(avg_seconds / 60, 1) if avg_seconds is not None else None,
        }

    def list_recent_activity_for_analyst(self, analyst_id: uuid.UUID, limit: int = 10) -> list[ReviewQueue]:
        stmt = (
            select(ReviewQueue)
            .options(*_EAGER_LOAD)
            .where(ReviewQueue.assigned_analyst_id == analyst_id, ReviewQueue.status == ReviewStatus.RESOLVED)
            .order_by(ReviewQueue.resolved_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())
