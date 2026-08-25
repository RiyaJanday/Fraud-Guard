"""add rules table and triggered_rules on fraud_predictions

Revision ID: c7d9e1f3a5b8
Revises: a1b2c3d4e5f6
Create Date: 2026-08-23T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7d9e1f3a5b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_type=False on each: we create these explicitly below (idempotent via
    # checkfirst=True), so the inline column definitions must NOT also try to
    # auto-create them during create_table — that double-creation is exactly
    # what caused "type already exists" on any run after the first.
    rule_field = postgresql.ENUM(
        'amount', 'currency', 'merchant', 'customer_reference', 'card_last4',
        'device_info', 'ip_address', 'location', 'time_feature',
        name='rule_field',
        create_type=False,
    )
    rule_operator = postgresql.ENUM(
        'gt', 'gte', 'lt', 'lte', 'eq', 'neq', 'contains',
        name='rule_operator',
        create_type=False,
    )
    rule_action = postgresql.ENUM(
        'notify', 'flag', 'block',
        name='rule_action',
        create_type=False,
    )
    rule_field.create(op.get_bind(), checkfirst=True)
    rule_operator.create(op.get_bind(), checkfirst=True)
    rule_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('field', rule_field, nullable=False),
        sa.Column('operator', rule_operator, nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('action', rule_action, nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_rules_enabled', 'rules', ['enabled'])
    op.create_index('ix_rules_id', 'rules', ['id'])
    op.create_index('ix_rules_created_at', 'rules', ['created_at'])

    op.add_column(
        'fraud_predictions',
        sa.Column(
            'triggered_rules',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
            comment='[{"rule_id": "...", "name": "...", "field": "amount", "operator": "gt", '
                    '"value": "50000", "action": "block"}, ...] — business rules (not the ML model) that matched this transaction.',
        ),
    )


def downgrade() -> None:
    op.drop_column('fraud_predictions', 'triggered_rules')
    op.drop_index('ix_rules_created_at', table_name='rules')
    op.drop_index('ix_rules_id', table_name='rules')
    op.drop_index('ix_rules_enabled', table_name='rules')
    op.drop_table('rules')

    postgresql.ENUM(name='rule_action').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='rule_operator').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='rule_field').drop(op.get_bind(), checkfirst=True)
