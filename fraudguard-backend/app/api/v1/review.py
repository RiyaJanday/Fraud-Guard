"""
Manual review workflow endpoints:

    GET  /review-queue              — list, filterable by status
    GET  /review-queue/{id}         — full detail
    POST /review-queue/{id}/claim   — an analyst claims it (optional step)
    POST /review-queue/{id}/resolve — analyst records fraud/legitimate ground truth
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.review import ReviewStatus
from app.models.user import User, UserRole
from app.schemas.review import ReviewListResponse, ReviewQueueDetailOut, ReviewQueueOut, ReviewResolveRequest
from app.services.review_service import ReviewService

router = APIRouter()

# Read-only for all three roles; only Admin/Analyst can claim or resolve (Auditor stays read-only).
_ANY_ROLE = (UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)
_ACTION_ROLES = (UserRole.ADMIN, UserRole.ANALYST)


@router.get("", response_model=ReviewListResponse, summary="List the manual review queue")
def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ReviewStatus] = Query(None, description="Filter by pending, in_review, or resolved"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> ReviewListResponse:
    return ReviewService(db).list_reviews(page=page, page_size=page_size, status=status)


@router.get(
    "/{review_id}",
    response_model=ReviewQueueDetailOut,
    summary="Get full review detail, including SHAP features",
)
def get_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ANY_ROLE)),
) -> ReviewQueueDetailOut:
    return ReviewService(db).get_review_detail(review_id)


@router.post(
    "/{review_id}/claim",
    response_model=ReviewQueueOut,
    summary="Claim a review (optional — signals to the team you're working on it)",
    responses={409: {"description": "Already resolved, or claimed by a different analyst."}},
)
def claim_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ACTION_ROLES)),
) -> ReviewQueueOut:
    return ReviewService(db).claim_review(review_id, current_user)


@router.post(
    "/{review_id}/resolve",
    response_model=ReviewQueueOut,
    summary="Resolve a review with a fraud/legitimate decision — this is the ground truth",
    description=(
        "Records the analyst's decision (fraud or legitimate) as ground truth for this "
        "transaction. Auto-claims the review if nobody claimed it first."
    ),
    responses={409: {"description": "Already resolved, or claimed by a different analyst."}},
)
def resolve_review(
    review_id: UUID,
    payload: ReviewResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*_ACTION_ROLES)),
) -> ReviewQueueOut:
    return ReviewService(db).resolve_review(review_id, payload, current_user)
