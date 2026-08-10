"""
GET  /model/status   — current active model's metrics + whether a retrain is running
POST /model/retrain   — admin-only: kicks off retraining as a background task

Retraining always runs in --quick mode here (fixed hyperparameters, no grid
search) — deliberately, not as an oversight. A full hyperparameter search
can run for tens of minutes; that's fine to run locally/deliberately via
`python train_model.py` (no time limit that matters), but a live "Retrain"
button an admin might click during a demo needs to actually finish in a
reasonable window on Render's free-tier CPU. If you want the full search,
run train_model.py directly and it registers the result the same way.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.model import ActiveModelOut, ModelStatusOut, RetrainTriggerResponse
from app.services import training_service

router = APIRouter()


@router.get(
    "/status",
    response_model=ModelStatusOut,
    summary="Current active model's metrics, plus whether a retrain is running",
)
def get_model_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR)),
) -> ModelStatusOut:
    active = ModelRegistryRepository(db).get_active()
    status = training_service.get_status()
    return ModelStatusOut(
        active_model=ActiveModelOut.model_validate(active) if active else None,
        training_in_progress=status["in_progress"],
        training_started_at=status["started_at"],
        training_finished_at=status["finished_at"],
        last_training_error=status["last_error"],
    )


@router.post(
    "/retrain",
    response_model=RetrainTriggerResponse,
    summary="Admin-only: trigger a retrain (runs in the background, --quick mode)",
    description=(
        "Returns immediately; the actual training run happens in a background "
        "thread and can take a few minutes. Poll GET /model/status to see when it "
        "finishes and what it produced. Refuses to start a second run if one is "
        "already in progress (see app/services/training_service.py)."
    ),
)
def trigger_retrain(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RetrainTriggerResponse:
    started = training_service.try_start()
    if not started:
        return RetrainTriggerResponse(message="A training run is already in progress.", training_in_progress=True)

    background_tasks.add_task(training_service.run_training_background, quick=True)
    return RetrainTriggerResponse(message="Retraining started.", training_in_progress=True)
