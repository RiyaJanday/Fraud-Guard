"""
Business logic for the transaction submission/scoring pipeline and for
listing/retrieving transactions.

submit_transaction() implements the full pipeline from the project spec:

    Transaction -> Validation -> Preprocessing -> XGBoost Prediction ->
    Risk Score -> SHAP Explanation -> Decision Engine -> Save Database ->
    Notify Dashboard

Every stage is recorded as a FraudLog row, giving a complete, queryable
audit trail per transaction — not just a log line in a file. The actual
preprocessing/prediction/SHAP/decision-engine work is NOT duplicated here;
it all happens inside app.ml_engine.predictor.FraudPredictor (Step 4), which
this service calls once and translates into persisted rows.

"Notify Dashboard" (the last pipeline stage) is now real as of Step 8: it
persists a Notification row and pushes it live over WebSocket via
NotificationService, and is logged as a genuine FraudLog stage below.
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ModelNotLoadedException, NotFoundException
from app.core.logging import logger
from app.core.websocket import manager as ws_manager
from app.ml_engine.predictor import get_predictor
from app.models.fraud_log import LogStatus, PipelineStage
from app.models.fraud_prediction import Decision, FraudPrediction
from app.models.transaction import Transaction
from app.repositories.fraud_log_repository import FraudLogRepository
from app.repositories.fraud_prediction_repository import FraudPredictionRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import (
    FraudLogOut,
    FraudPredictionOut,
    TransactionCreate,
    TransactionDetailOut,
    TransactionListResponse,
    TransactionOut,
    TransactionReviewSummary,
)
from app.services.notification_service import NotificationService
from app.services.review_service import ReviewService


class TransactionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.transactions = TransactionRepository(db)
        self.predictions = FraudPredictionRepository(db)
        self.logs = FraudLogRepository(db)
        self.model_registry = ModelRegistryRepository(db)
        self.review_repo = ReviewRepository(db)
        self.reviews = ReviewService(db)
        self.notifications = NotificationService(db)

    # ------------------------------------------------------------------ #
    # Submission / scoring pipeline
    # ------------------------------------------------------------------ #
    def submit_transaction(
        self, payload: TransactionCreate, submitted_by_id: Optional[uuid.UUID]
    ) -> Transaction:
        # Stage 1: Validation — Pydantic already validated the request shape
        # (including that all 28 V-features are present); persisting the
        # transaction row IS the validation stage completing successfully.
        transaction = Transaction(
            time_feature=payload.time_feature,
            amount=payload.amount,
            v_features=payload.v_features,
            currency=payload.currency,
            merchant=payload.merchant,
            customer_reference=payload.customer_reference,
            card_last4=payload.card_last4,
            device_info=payload.device_info,
            ip_address=payload.ip_address,
            location=payload.location,
            submitted_by_id=submitted_by_id,
        )
        transaction = self.transactions.create(transaction)
        self.logs.create(
            transaction.id, PipelineStage.VALIDATION, LogStatus.SUCCESS, "Transaction data validated and persisted."
        )

        # Stages 2-6: Preprocessing, XGBoost Prediction, Risk Score, SHAP
        # Explanation, Decision Engine — all handled inside FraudPredictor
        # (Step 4). This service never reimplements or duplicates that logic.
        try:
            result = get_predictor().predict(
                time_feature=payload.time_feature, amount=payload.amount, v_features=payload.v_features
            )
        except ModelNotLoadedException as exc:
            self.logs.create(
                transaction.id, PipelineStage.PREDICTION, LogStatus.FAILURE, "No trained model available."
            )
            logger.error("Prediction failed for transaction {}: {}", transaction.id, exc.message)
            raise
        except Exception as exc:  # noqa: BLE001 — log whatever went wrong, then re-raise
            self.logs.create(transaction.id, PipelineStage.PREDICTION, LogStatus.FAILURE, str(exc))
            logger.exception("Unexpected error scoring transaction {}", transaction.id)
            raise

        self.logs.create(
            transaction.id, PipelineStage.PREPROCESSING, LogStatus.SUCCESS, "Features engineered and scaled."
        )
        self.logs.create(
            transaction.id,
            PipelineStage.PREDICTION,
            LogStatus.SUCCESS,
            f"Model {result['model_version']} scored transaction (latency {result['latency_ms']}ms).",
        )
        self.logs.create(
            transaction.id,
            PipelineStage.DECISION,
            LogStatus.SUCCESS,
            f"Decision: {result['decision'].value} (risk score {result['risk_score']}).",
        )

        # Stage 7: Save Database
        active_model = self.model_registry.get_active()
        prediction = FraudPrediction(
            transaction_id=transaction.id,
            model_registry_id=active_model.id if active_model else None,
            model_version=result["model_version"],
            is_fraud=result["is_fraud"],
            fraud_probability=result["fraud_probability"],
            risk_score=result["risk_score"],
            confidence=result["confidence"],
            decision=result["decision"],
            latency_ms=result["latency_ms"],
            top_shap_features=result["top_shap_features"],
            explanation=result["explanation"],
        )
        prediction = self.predictions.create(prediction)
        self.logs.create(
            transaction.id, PipelineStage.PERSISTENCE, LogStatus.SUCCESS, "Prediction saved to database."
        )

        # High-risk (BLOCKED) predictions automatically enter the manual
        # review queue — see ReviewService.create_review_if_needed for why
        # the threshold is BLOCKED specifically, not MFA_REQUIRED too.
        self.reviews.create_review_if_needed(prediction)

        # Stage 8: Notify Dashboard — persists a Notification row and pushes
        # it live over WebSocket in the same call. Now that this actually
        # does something (Step 8), it earns a real FraudLog entry, unlike
        # before (see this module's docstring for why it was omitted).
        notification = self.notifications.notify_for_prediction(transaction, prediction)
        self.logs.create(
            transaction.id,
            PipelineStage.NOTIFICATION,
            LogStatus.SUCCESS,
            f"Dashboard notified (id={notification.id})." if notification else "No notification needed (approved).",
        )

        logger.info(
            "Transaction scored | id={} decision={} risk_score={} model={}",
            transaction.id, prediction.decision.value, prediction.risk_score, prediction.model_version,
        )

        transaction.prediction = prediction

        # Live Monitoring feed: broadcasts EVERY scored transaction (unlike
        # NotificationService above, which only fires for BLOCKED/MFA_REQUIRED)
        # over the same WebSocket channel, under a distinct "transaction_scored"
        # event so the notification bell and the live feed can share one
        # connection without stepping on each other — the frontend simply
        # ignores events it doesn't care about. This is what actually powers
        # the Live Monitoring page's real-time feed.
        ws_manager.broadcast_sync({
            "event": "transaction_scored",
            "transaction": {
                "id": str(transaction.id),
                "merchant": transaction.merchant,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "risk_score": prediction.risk_score,
                "decision": prediction.decision.value,
                "is_fraud": prediction.is_fraud,
                "created_at": transaction.created_at.isoformat(),
            },
        })

        return transaction

    # ------------------------------------------------------------------ #
    # Read paths
    # ------------------------------------------------------------------ #
    def get_transaction_detail(self, transaction_id: uuid.UUID) -> TransactionDetailOut:
        transaction = self.transactions.get_by_id(transaction_id)
        if transaction is None:
            raise NotFoundException(f"Transaction {transaction_id} was not found.")
        return self.to_detail_out(transaction)

    def list_transactions(
        self,
        page: int,
        page_size: int,
        decision: Optional[Decision] = None,
        min_risk_score: Optional[float] = None,
        max_risk_score: Optional[float] = None,
        merchant: Optional[str] = None,
        date_from=None,
        date_to=None,
    ) -> TransactionListResponse:
        items, total = self.transactions.list_paginated(
            page=page,
            page_size=page_size,
            decision=decision,
            min_risk=min_risk_score,
            max_risk=max_risk_score,
            merchant=merchant,
            date_from=date_from,
            date_to=date_to,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return TransactionListResponse(
            items=[TransactionOut.from_transaction(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ------------------------------------------------------------------ #
    # Shared helper
    # ------------------------------------------------------------------ #
    def to_detail_out(self, transaction: Transaction) -> TransactionDetailOut:
        logs = self.logs.list_by_transaction(transaction.id)
        prediction_out = FraudPredictionOut.model_validate(transaction.prediction) if transaction.prediction else None

        # Only BLOCKED transactions ever get a review row (see
        # ReviewService.create_review_if_needed) — for everything else this
        # stays None, which the frontend uses to decide whether to even show
        # the Confirm/Escalate actions at all.
        review_out = None
        if transaction.prediction:
            review = self.review_repo.get_by_prediction_id(transaction.prediction.id)
            if review:
                review_out = TransactionReviewSummary(
                    id=review.id,
                    status=review.status,
                    analyst_decision=review.analyst_decision,
                    assigned_analyst_name=review.analyst.full_name if review.analyst else None,
                    notes=review.notes,
                    resolved_at=review.resolved_at,
                )

        return TransactionDetailOut(
            id=transaction.id,
            time_feature=transaction.time_feature,
            amount=transaction.amount,
            currency=transaction.currency,
            v_features=transaction.v_features,
            merchant=transaction.merchant,
            customer_reference=transaction.customer_reference,
            card_last4=transaction.card_last4,
            device_info=transaction.device_info,
            ip_address=transaction.ip_address,
            location=transaction.location,
            created_at=transaction.created_at,
            prediction=prediction_out,
            decision_history=[FraudLogOut.model_validate(log) for log in logs],
            review=review_out,
        )
