"""GET /drift — data drift check comparing live traffic to the training distribution."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.drift import DriftReportOut
from app.services.drift_service import DriftService

router = APIRouter()

_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get(
    "",
    response_model=DriftReportOut,
    summary="Check for data drift between live traffic and the training distribution",
    description=(
        "Runs a two-sample Kolmogorov-Smirnov test per feature (V1-V28, Amount), comparing "
        "the most recent live transactions against a cached sample of the original training "
        "dataset. Returns 'insufficient_data' instead of a verdict if fewer than 30 live "
        "transactions have been scored yet — not enough to test responsibly."
    ),
)
def get_drift_report(
    sample_size: int = Query(500, ge=30, le=5000, description="How many recent transactions to sample"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> DriftReportOut:
    return DriftService(db).get_drift_report(sample_size=sample_size)
