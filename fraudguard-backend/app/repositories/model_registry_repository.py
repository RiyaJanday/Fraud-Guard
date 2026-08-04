"""Raw database access for ModelRegistry — used here to look up whichever model is ACTIVE."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_metrics import ModelMetrics
from app.models.model_registry import ModelRegistry, ModelStatus


class ModelRegistryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active(self) -> Optional[ModelRegistry]:
        stmt = select(ModelRegistry).where(ModelRegistry.status == ModelStatus.ACTIVE)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_metrics(self, model_registry_id) -> Optional[ModelMetrics]:
        """Most recent evaluation snapshot for a model — confusion matrix included.
        Returns None if train_model.py never recorded one (older model artifacts)."""
        stmt = (
            select(ModelMetrics)
            .where(ModelMetrics.model_registry_id == model_registry_id)
            .order_by(ModelMetrics.recorded_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
