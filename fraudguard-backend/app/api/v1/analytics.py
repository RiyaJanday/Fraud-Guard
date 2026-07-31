"""GET /analytics — deeper analytics: merchant risk, geography-equivalent breakdowns."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import AnalyticsOut
from app.services.analytics_service import AnalyticsService

router = APIRouter()

_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get("", response_model=AnalyticsOut, summary="Fraud analytics: trends, distribution, top-risk merchants")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> AnalyticsOut:
    return AnalyticsService(db).get_analytics()
