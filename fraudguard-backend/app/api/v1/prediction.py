"""POST /predict — real-time fraud scoring endpoint."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.transaction import TransactionCreate, TransactionDetailOut
from app.services.transaction_service import TransactionService

router = APIRouter()
settings = get_settings()


@router.post(
    "/predict",
    response_model=TransactionDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a transaction for real-time fraud scoring",
    description=(
        "Runs the full pipeline: validation \u2192 preprocessing \u2192 XGBoost "
        "prediction \u2192 risk scoring \u2192 SHAP explanation \u2192 decision engine \u2192 "
        "persistence. Returns the prediction, fraud probability, risk score, "
        "confidence, suggested action (decision), and SHAP explainability — "
        "plus the full per-stage decision history."
    ),
    responses={
        503: {"description": "No trained model is available yet — run train_model.py first."},
    },
)
@limiter.limit(settings.RATE_LIMIT_PREDICT)
def predict(
    request: Request,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
) -> TransactionDetailOut:
    service = TransactionService(db)
    transaction = service.submit_transaction(payload, submitted_by_id=current_user.id)
    return service.to_detail_out(transaction)
