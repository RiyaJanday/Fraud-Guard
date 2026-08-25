"""
Stateless evaluation logic for business rules against a raw transaction.

Deliberately operates on the fields available at submission time (see
TransactionCreate) rather than on the ML model's output — a rule match
should never depend on the model having run first. This is what lets a
rule like "always block first-ever transactions over 50,000" function as
genuine, model-independent business policy rather than a second opinion on
the model's own judgment.

Severity ordering for combining multiple matched rules' actions:
NOTIFY < FLAG < BLOCK. If several rules match, the strongest action wins —
a NOTIFY-only rule never suppresses a BLOCK rule that also matched.
"""

from dataclasses import dataclass
from typing import Optional

from app.models.rule import Rule, RuleAction, RuleOperator

_ACTION_SEVERITY = {RuleAction.NOTIFY: 0, RuleAction.FLAG: 1, RuleAction.BLOCK: 2}

# Fields whose values are compared numerically. Anything not listed here is
# compared as text (case-insensitive for eq/neq/contains).
_NUMERIC_FIELDS = {"amount", "time_feature"}


@dataclass
class TriggeredRule:
    rule: Rule


def _coerce(field_value, rule_value: str, numeric: bool):
    if not numeric:
        return (str(field_value) if field_value is not None else "").lower(), rule_value.lower()
    try:
        return float(field_value), float(rule_value)
    except (TypeError, ValueError):
        # A numeric field with a value that can't be parsed (e.g. field is
        # None, or the rule's stored value is malformed) never matches,
        # rather than raising and taking the whole prediction pipeline down.
        return None, None


def _compare(left, right, operator: RuleOperator) -> bool:
    if left is None or right is None:
        return False
    if operator == RuleOperator.GT:
        return left > right
    if operator == RuleOperator.GTE:
        return left >= right
    if operator == RuleOperator.LT:
        return left < right
    if operator == RuleOperator.LTE:
        return left <= right
    if operator == RuleOperator.EQ:
        return left == right
    if operator == RuleOperator.NEQ:
        return left != right
    if operator == RuleOperator.CONTAINS:
        return isinstance(left, str) and isinstance(right, str) and right in left
    return False  # pragma: no cover — exhaustive over RuleOperator


def rule_matches(rule: Rule, transaction_fields: dict) -> bool:
    field_value = transaction_fields.get(rule.field.value)
    numeric = rule.field.value in _NUMERIC_FIELDS
    left, right = _coerce(field_value, rule.value, numeric)
    return _compare(left, right, rule.operator)


def evaluate_rules(rules: list[Rule], transaction_fields: dict) -> list[Rule]:
    """Returns every enabled rule that matches this transaction, evaluated
    against a plain dict of {field_name: value} (matching RuleField's
    values) — the caller builds that dict from whatever it has on hand
    (a TransactionCreate payload, an ORM Transaction, etc.) so this module
    stays decoupled from any one of those shapes."""
    return [r for r in rules if r.enabled and rule_matches(r, transaction_fields)]


def strongest_action(matched: list[Rule]) -> Optional[RuleAction]:
    if not matched:
        return None
    return max((r.action for r in matched), key=lambda a: _ACTION_SEVERITY[a])
