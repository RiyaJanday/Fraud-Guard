"""add notification_preferences to users

Revision ID: a1b2c3d4e5f6
Revises: eb7fc4bd2c12
Create Date: 2026-08-01T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'eb7fc4bd2c12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'notification_preferences',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='e.g. {"blocked_transaction": true, "high_risk_alert": true, "review_required": false}. '
                    'Missing keys are treated as enabled by default (see NotificationService).',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'notification_preferences')
