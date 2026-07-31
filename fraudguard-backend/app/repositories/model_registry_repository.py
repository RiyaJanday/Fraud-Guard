"""Raw database access for ModelRegistry — used here to look up whichever model is ACTIVE."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistry, ModelStatus


class ModelRegistryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active(self) -> Optional[ModelRegistry]:
        stmt = select(ModelRegistry).where(ModelRegistry.status == ModelStatus.ACTIVE)
        return self.db.execute(stmt).scalar_one_or_none()
