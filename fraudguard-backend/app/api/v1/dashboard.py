"""GET /dashboard/stats, /dashboard/charts, /dashboard/alerts — the data behind the frontend Dashboard page."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.dashboard import AlertOut, DashboardChartsOut, DashboardStatsOut
from app.services.analytics_service import AnalyticsService

router = APIRouter()

# Read-only for everyone — all three roles can view the dashboard.
_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get("/stats", response_model=DashboardStatsOut, summary="Top-level dashboard statistics")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> DashboardStatsOut:
    return AnalyticsService(db).get_dashboard_stats()


@router.get("/charts", response_model=DashboardChartsOut, summary="All dashboard chart datasets in one response")
def get_dashboard_charts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> DashboardChartsOut:
    return AnalyticsService(db).get_dashboard_charts()


@router.get("/alerts", response_model=list[AlertOut], summary="Recent high-risk alerts")
def get_dashboard_alerts(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> list[AlertOut]:
    return AnalyticsService(db).get_recent_alerts(limit=limit)
