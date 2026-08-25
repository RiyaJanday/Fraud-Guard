"""Raw database access for Rule records."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rule import Rule


class RuleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, rule: Rule) -> Rule:
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def save(self, rule: Rule) -> Rule:
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_by_id(self, rule_id: uuid.UUID) -> Optional[Rule]:
        return self.db.get(Rule, rule_id)

    def delete(self, rule: Rule) -> None:
        self.db.delete(rule)
        self.db.commit()

    def list_all(self, enabled_only: bool = False) -> list[Rule]:
        stmt = select(Rule).order_by(Rule.created_at.desc())
        if enabled_only:
            stmt = stmt.where(Rule.enabled.is_(True))
        return list(self.db.execute(stmt).scalars().all())
