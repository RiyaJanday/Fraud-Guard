"""Admin-facing CRUD for business rules (app/models/rule.py)."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.rule import Rule, RuleAction
from app.models.user import User
from app.repositories.rule_repository import RuleRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.rule import (
    RuleCreate,
    RuleListResponse,
    RuleOut,
    RulePreviewMatchOut,
    RulePreviewRequest,
    RulePreviewResponse,
    RuleUpdate,
)
from app.services.rule_engine import rule_matches


class RuleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rules = RuleRepository(db)
        self.transactions = TransactionRepository(db)

    def list_rules(self) -> RuleListResponse:
        items = self.rules.list_all()
        return RuleListResponse(items=[self._to_out(r) for r in items], total=len(items))

    def create_rule(self, payload: RuleCreate, created_by: User) -> RuleOut:
        rule = Rule(
            name=payload.name,
            field=payload.field,
            operator=payload.operator,
            value=payload.value,
            action=payload.action,
            enabled=payload.enabled,
            created_by_id=created_by.id,
        )
        rule = self.rules.create(rule)
        logger.info("Rule created | id={} name={!r} by={}", rule.id, rule.name, created_by.id)
        return self._to_out(rule)

    def update_rule(self, rule_id: uuid.UUID, payload: RuleUpdate) -> RuleOut:
        rule = self._get_or_404(rule_id)
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(rule, key, value)
        rule = self.rules.save(rule)
        logger.info("Rule updated | id={} fields={}", rule.id, list(updates.keys()))
        return self._to_out(rule)

    def delete_rule(self, rule_id: uuid.UUID) -> None:
        rule = self._get_or_404(rule_id)
        self.rules.delete(rule)
        logger.info("Rule deleted | id={}", rule_id)

    def preview_rule(self, payload: RulePreviewRequest) -> RulePreviewResponse:
        """
        Tests a proposed rule definition against real recent transactions
        WITHOUT persisting anything — lets an admin sanity-check "how many
        of my last 200 transactions would this have caught" before
        committing to a rule that might be too broad (e.g. accidentally
        matching most of your traffic) or too narrow to matter.

        Builds a throwaway, unsaved Rule instance purely to reuse
        rule_engine.rule_matches's comparison logic — never added to the
        session, so it can never accidentally get flushed to the database.
        """
        candidate = Rule(
            name="__preview__", field=payload.field, operator=payload.operator,
            value=payload.value, action=RuleAction.NOTIFY, enabled=True,
        )
        recent = self.transactions.list_recent(limit=payload.sample_size)

        matches = []
        for txn in recent:
            fields = {
                "amount": txn.amount,
                "currency": txn.currency,
                "merchant": txn.merchant,
                "customer_reference": txn.customer_reference,
                "card_last4": txn.card_last4,
                "device_info": txn.device_info,
                "ip_address": txn.ip_address,
                "location": txn.location,
                "time_feature": txn.time_feature,
            }
            if rule_matches(candidate, fields):
                matches.append(
                    RulePreviewMatchOut(
                        transaction_id=txn.id,
                        merchant=txn.merchant,
                        amount=txn.amount,
                        decision=txn.prediction.decision.value if txn.prediction else None,
                        created_at=txn.created_at,
                    )
                )

        return RulePreviewResponse(sample_size=len(recent), match_count=len(matches), matches=matches[:25])

    def _get_or_404(self, rule_id: uuid.UUID) -> Rule:
        rule = self.rules.get_by_id(rule_id)
        if rule is None:
            raise NotFoundException(f"Rule {rule_id} was not found.")
        return rule

    @staticmethod
    def _to_out(rule: Rule) -> RuleOut:
        return RuleOut(
            id=rule.id,
            name=rule.name,
            field=rule.field,
            operator=rule.operator,
            value=rule.value,
            action=rule.action,
            enabled=rule.enabled,
            created_by_id=rule.created_by_id,
            created_by_name=rule.created_by.full_name if rule.created_by else None,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
