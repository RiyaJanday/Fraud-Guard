"""GET /transactions and GET /transactions/{id} — listing and detail views."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.fraud_prediction import Decision
from app.models.user import User, UserRole
from app.schemas.transaction import TransactionDetailOut, TransactionListResponse
from app.services.transaction_service import TransactionService

router = APIRouter()

# Read-only endpoints — all three roles can view transactions; only Admin/Analyst can submit them (see prediction.py).
_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="List transactions with filtering and pagination",
)
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    decision: Optional[Decision] = Query(None, description="Filter by decision: approve, mfa_required, or blocked"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100),
    merchant: Optional[str] = Query(None, description="Case-insensitive partial match"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> TransactionListResponse:
    service = TransactionService(db)
    return service.list_transactions(
        page=page,
        page_size=page_size,
        decision=decision,
        min_risk_score=min_risk_score,
        max_risk_score=max_risk_score,
        merchant=merchant,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailOut,
    summary="Get full transaction detail, including prediction, SHAP features, and decision history",
)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> TransactionDetailOut:
    service = TransactionService(db)
    return service.get_transaction_detail(transaction_id)
