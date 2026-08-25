"""
Admin-only CRUD for business rules that run alongside the ML model:

    GET    /rules       — list every rule (any authenticated role — analysts
                           should be able to see what policy is active, same
                           as they can see model info, even if only Admin
                           can change it)
    POST   /rules       — create a rule (admin only)
    PATCH  /rules/{id}  — update a rule, e.g. toggle enabled (admin only)
    DELETE /rules/{id}  — remove a rule (admin only)

Rules take effect immediately on the next /predict call — there is no
separate "publish" step, since RuleRepository.list_all(enabled_only=True)
is queried fresh on every transaction (see rule evaluation hook in
transaction_service.py).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.rule import RuleCreate, RuleListResponse, RuleOut, RulePreviewRequest, RulePreviewResponse, RuleUpdate
from app.services.rule_service import RuleService

router = APIRouter()

_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)


@router.get("", response_model=RuleListResponse, summary="List every business rule")
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> RuleListResponse:
    return RuleService(db).list_rules()


@router.post(
    "/preview",
    response_model=RulePreviewResponse,
    summary="Test a proposed (unsaved) rule against recent transactions (admin only)",
    description=(
        "Registered BEFORE /{rule_id} deliberately — same reasoning as "
        "review.py's /audit-log route: 'preview' would otherwise incorrectly "
        "attempt to parse as a {rule_id}: UUID and 422 instead of matching here. "
        "Nothing is persisted; this only reports how many of the most recent "
        "N transactions the given field/operator/value would have matched."
    ),
)
def preview_rule(
    payload: RulePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RulePreviewResponse:
    return RuleService(db).preview_rule(payload)


@router.post(
    "",
    response_model=RuleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a business rule (admin only)",
)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RuleOut:
    return RuleService(db).create_rule(payload, created_by=current_user)


@router.patch(
    "/{rule_id}",
    response_model=RuleOut,
    summary="Update a business rule, e.g. toggle enabled (admin only)",
    responses={404: {"description": "Rule not found."}},
)
def update_rule(
    rule_id: UUID,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RuleOut:
    return RuleService(db).update_rule(rule_id, payload)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a business rule (admin only)",
    responses={404: {"description": "Rule not found."}},
)
def delete_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    RuleService(db).delete_rule(rule_id)
