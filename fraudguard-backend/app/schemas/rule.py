"""Pydantic schemas for the business-rules engine (app/models/rule.py)."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.rule import RuleAction, RuleField, RuleOperator


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    field: RuleField
    operator: RuleOperator
    value: str = Field(..., min_length=1, max_length=255)
    action: RuleAction
    enabled: bool = True


class RuleUpdate(BaseModel):
    """PATCH /rules/{id} — every field optional, only supplied ones change."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    field: Optional[RuleField] = None
    operator: Optional[RuleOperator] = None
    value: Optional[str] = Field(default=None, min_length=1, max_length=255)
    action: Optional[RuleAction] = None
    enabled: Optional[bool] = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    field: RuleField
    operator: RuleOperator
    value: str
    action: RuleAction
    enabled: bool
    created_by_id: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    items: List[RuleOut]
    total: int


class TriggeredRuleOut(BaseModel):
    """One entry in FraudPrediction.triggered_rules — a snapshot of the rule
    as it existed at evaluation time, not a live reference, so history stays
    accurate even if the rule is later edited or deleted."""

    rule_id: uuid.UUID
    name: str
    field: RuleField
    operator: RuleOperator
    value: str
    action: RuleAction


class RulePreviewRequest(BaseModel):
    """POST /rules/preview request body — tests an unsaved rule definition
    against real recent transactions before an admin commits to creating it."""

    field: RuleField
    operator: RuleOperator
    value: str = Field(..., min_length=1, max_length=255)
    sample_size: int = Field(default=200, ge=1, le=1000, description="How many of the most recent transactions to test against")


class RulePreviewMatchOut(BaseModel):
    transaction_id: uuid.UUID
    merchant: Optional[str] = None
    amount: float
    decision: Optional[str] = None
    created_at: datetime


class RulePreviewResponse(BaseModel):
    sample_size: int = Field(..., description="How many recent transactions were actually tested")
    match_count: int
    matches: List[RulePreviewMatchOut]
