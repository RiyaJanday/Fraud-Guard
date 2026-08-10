"""
Business logic for the manual review workflow:

    Prediction -> (BLOCKED or MFA_REQUIRED) -> Manual Review Queue ->
    Analyst Decision (fraud/legitimate) -> ground truth stored for future
    retraining.

Both BLOCKED and MFA_REQUIRED predictions enter this queue. Originally only
BLOCKED did (MFA_REQUIRED was assumed to resolve itself via an automated
step-up-auth challenge outside this system's scope) — widened per this
module's own prior note that it would be "easy to widen later... if
MFA_REQUIRED transactions turn out to need review too," which they do: this
project has no actual OTP/step-up channel, so an MFA-flagged transaction
with no review path was a dead end with no way to ever resolve it. Routing
it through the same analyst-reviewed queue as BLOCKED transactions is more
honest than simulating a fake OTP screen, and reuses an already-working,
already-tested claim/resolve flow instead of building a parallel one.

Ground truth capture: resolve_review's `analyst_decision` (FRAUD /
LEGITIMATE) IS the ground truth label future retraining would use — that's
the whole point of this table existing separately from FraudPrediction.
Actually wiring that into a retraining pipeline is future work, not part of
this step.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import logger
from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.review import ReviewQueue, ReviewStatus
from app.models.user import User
from app.repositories.review_repository import ReviewRepository
from app.schemas.review import (
    ReviewListResponse,
    ReviewQueueDetailOut,
    ReviewQueueOut,
    ReviewResolveRequest,
)
from app.schemas.transaction import ShapFeatureOut
from app.schemas.user import ProfileActivityItemOut, ProfileStatsOut


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reviews = ReviewRepository(db)

    # ------------------------------------------------------------------ #
    # Called by TransactionService right after a prediction is persisted.
    # ------------------------------------------------------------------ #
    def create_review_if_needed(self, prediction: FraudPrediction) -> Optional[ReviewQueue]:
        if prediction.decision not in (Decision.BLOCKED, Decision.MFA_REQUIRED):
            return None
        review = self.reviews.create(prediction.id)
        logger.info(
            "Transaction {} auto-queued for manual review | review_id={} decision={}",
            prediction.transaction_id, review.id, prediction.decision.value,
        )
        return review

    # ------------------------------------------------------------------ #
    # Read paths
    # ------------------------------------------------------------------ #
    def list_reviews(self, page: int, page_size: int, status: Optional[ReviewStatus] = None) -> ReviewListResponse:
        items, total = self.reviews.list_paginated(page=page, page_size=page_size, status=status)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return ReviewListResponse(
            items=[self._to_out(r) for r in items], total=total, page=page, page_size=page_size, total_pages=total_pages
        )

    def list_audit_log(self, page: int, page_size: int) -> ReviewListResponse:
        """Admin-only compliance view — every resolved review across every
        analyst, newest first. See ReviewRepository.list_all_resolved."""
        items, total = self.reviews.list_all_resolved(page=page, page_size=page_size)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return ReviewListResponse(
            items=[self._to_out(r) for r in items], total=total, page=page, page_size=page_size, total_pages=total_pages
        )

    def get_review_detail(self, review_id: uuid.UUID) -> ReviewQueueDetailOut:
        review = self.reviews.get_by_id(review_id)
        if review is None:
            raise NotFoundException(f"Review {review_id} was not found.")
        return self._to_detail_out(review)

    # ------------------------------------------------------------------ #
    # Write paths
    # ------------------------------------------------------------------ #
    def claim_review(self, review_id: uuid.UUID, analyst: User) -> ReviewQueueOut:
        """
        Optional step for team visibility ("I'm working on this one") — NOT
        required before resolve_review, which auto-assigns the resolver if
        nobody claimed it first. Prevents two analysts from silently working
        the same review, but doesn't force a rigid two-step flow on a solo
        analyst.
        """
        review = self._get_or_404(review_id)
        self._ensure_not_resolved(review)
        if review.status == ReviewStatus.IN_REVIEW and review.assigned_analyst_id != analyst.id:
            raise ConflictException("This review is already claimed by another analyst.")

        review.status = ReviewStatus.IN_REVIEW
        review.assigned_analyst_id = analyst.id
        review = self.reviews.save(review)
        logger.info("Review claimed | id={} analyst={}", review.id, analyst.id)
        return self._to_out(review)

    def resolve_review(self, review_id: uuid.UUID, payload: ReviewResolveRequest, analyst: User) -> ReviewQueueOut:
        review = self._get_or_404(review_id)
        self._ensure_not_resolved(review)
        if review.status == ReviewStatus.IN_REVIEW and review.assigned_analyst_id not in (None, analyst.id):
            raise ConflictException("This review is claimed by another analyst — ask them to resolve it, or reassign it first.")

        review.status = ReviewStatus.RESOLVED
        review.analyst_decision = payload.decision
        review.notes = payload.notes
        review.assigned_analyst_id = analyst.id  # auto-claims if it wasn't already
        review.resolved_at = datetime.now(timezone.utc)
        review = self.reviews.save(review)
        logger.info(
            "Review resolved | id={} ground_truth={} analyst={}", review.id, payload.decision.value, analyst.id
        )
        return self._to_out(review)

    # ------------------------------------------------------------------ #
    # Shared helpers
    # ------------------------------------------------------------------ #
    def _get_or_404(self, review_id: uuid.UUID) -> ReviewQueue:
        review = self.reviews.get_by_id(review_id)
        if review is None:
            raise NotFoundException(f"Review {review_id} was not found.")
        return review

    @staticmethod
    def _ensure_not_resolved(review: ReviewQueue) -> None:
        if review.status == ReviewStatus.RESOLVED:
            raise ConflictException("This review has already been resolved.")

    def _to_out(self, review: ReviewQueue) -> ReviewQueueOut:
        pred = review.fraud_prediction
        txn = pred.transaction
        return ReviewQueueOut(
            id=review.id,
            fraud_prediction_id=review.fraud_prediction_id,
            status=review.status,
            assigned_analyst_id=review.assigned_analyst_id,
            assigned_analyst_name=review.analyst.full_name if review.analyst else None,
            analyst_decision=review.analyst_decision,
            notes=review.notes,
            resolved_at=review.resolved_at,
            created_at=review.created_at,
            transaction_id=txn.id,
            amount=txn.amount,
            merchant=txn.merchant,
            risk_score=pred.risk_score,
            fraud_probability=pred.fraud_probability,
            decision=pred.decision,
            explanation=pred.explanation,
        )

    def _to_detail_out(self, review: ReviewQueue) -> ReviewQueueDetailOut:
        base = self._to_out(review)
        pred = review.fraud_prediction
        txn = pred.transaction
        return ReviewQueueDetailOut(
            **base.model_dump(),
            top_shap_features=[ShapFeatureOut(**f) for f in pred.top_shap_features],
            v_features=txn.v_features,
            time_feature=txn.time_feature,
            currency=txn.currency,
        )

    # ------------------------------------------------------------------ #
    # Profile page — real per-analyst stats and activity, computed from
    # this SAME review-queue data rather than a fabricated "accuracy" number.
    # ------------------------------------------------------------------ #
    def get_profile_stats(self, analyst_id: uuid.UUID) -> ProfileStatsOut:
        return ProfileStatsOut(**self.reviews.get_stats_for_analyst(analyst_id))

    def get_recent_activity(self, analyst_id: uuid.UUID, limit: int = 10) -> List[ProfileActivityItemOut]:
        reviews = self.reviews.list_recent_activity_for_analyst(analyst_id, limit=limit)
        return [
            ProfileActivityItemOut(
                transaction_id=r.fraud_prediction.transaction_id,
                merchant=r.fraud_prediction.transaction.merchant if r.fraud_prediction.transaction else None,
                analyst_decision=r.analyst_decision.value if r.analyst_decision else None,
                resolved_at=r.resolved_at,
            )
            for r in reviews
        ]
