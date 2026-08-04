"""GET /explainability — global model card + real, data-driven feature importance."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.explainability import ExplainabilityOut
from app.services.explainability_service import ExplainabilityService

router = APIRouter()

_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get(
    "",
    response_model=ExplainabilityOut,
    summary="Global model explainability: model card, feature importance, example explanations",
)
def get_explainability(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> ExplainabilityOut:
    return ExplainabilityService(db).get_explainability()
