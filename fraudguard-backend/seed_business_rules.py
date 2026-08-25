"""
One-off script: seed the `rules` table with a realistic starter set of
business rules via the real Rule model (not hardcoded into app logic) — so
they show up immediately in the Business Rules admin page and are evaluated
by rule_engine.py on every /predict call, exactly like a rule an admin
created by hand through the UI.

Idempotent: skips any rule whose `name` already exists, so it's safe to
re-run (e.g. after adding a new entry to RULES below) without creating
duplicates.

Usage (from fraudguard-backend, with .venv active):
    python seed_business_rules.py
"""

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.rule import Rule, RuleAction, RuleField, RuleOperator
from app.models.user import User, UserRole

RULES = [
    {
        "name": "Block very large first-time transactions",
        "field": RuleField.AMOUNT,
        "operator": RuleOperator.GT,
        "value": "50000",
        "action": RuleAction.BLOCK,
    },
    {
        "name": "Flag high-value transactions",
        "field": RuleField.AMOUNT,
        "operator": RuleOperator.GT,
        "value": "20000",
        "action": RuleAction.FLAG,
    },
    {
        "name": "Notify on foreign currency",
        "field": RuleField.CURRENCY,
        "operator": RuleOperator.NEQ,
        "value": "INR",
        "action": RuleAction.NOTIFY,
    },
    {
        "name": "Block known high-risk merchant category",
        "field": RuleField.MERCHANT,
        "operator": RuleOperator.CONTAINS,
        "value": "Crypto",
        "action": RuleAction.BLOCK,
    },
    {
        "name": "Flag suspicious IP pattern",
        "field": RuleField.IP_ADDRESS,
        "operator": RuleOperator.CONTAINS,
        "value": "0.0.0.0",
        "action": RuleAction.FLAG,
    },
    {
        "name": "Flag odd-hour transactions",
        "field": RuleField.TIME_FEATURE,
        "operator": RuleOperator.GT,
        "value": "144000",
        "action": RuleAction.FLAG,
    },
    {
        "name": "Notify on missing device info",
        "field": RuleField.DEVICE_INFO,
        "operator": RuleOperator.EQ,
        "value": "",
        "action": RuleAction.NOTIFY,
    },
]


def main() -> None:
    get_settings()  # fail fast if .env is misconfigured, before opening a session
    db = SessionLocal()
    try:
        # Attribute created_by to the first admin, if one exists — purely
        # cosmetic (shows up in the UI's "created by" field), never required.
        admin = db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.created_at).first()

        existing_names = {r.name for r in db.query(Rule.name).all()}
        created = 0
        for spec in RULES:
            if spec["name"] in existing_names:
                print(f"Skipping (already exists): {spec['name']}")
                continue
            rule = Rule(
                name=spec["name"],
                field=spec["field"],
                operator=spec["operator"],
                value=spec["value"],
                action=spec["action"],
                enabled=True,
                created_by_id=admin.id if admin else None,
            )
            db.add(rule)
            created += 1
            print(f"Created: {spec['name']} ({spec['field'].value} {spec['operator'].value} {spec['value']!r} -> {spec['action'].value})")

        db.commit()
        print(f"\nDone. {created} rule(s) created, {len(RULES) - created} skipped (already present).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
