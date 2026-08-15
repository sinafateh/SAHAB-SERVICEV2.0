"""update workflow transitions

Revision ID: b90da6a9cb86
Revises: d8e2610201c5
Create Date: 2026-08-09 11:54:17.875082
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b90da6a9cb86"
down_revision: Union[str, Sequence[str], None] = "d8e2610201c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_transitions",
        sa.Column(
            "stage",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "workflow_transitions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_transitions", "updated_at")
    op.drop_column("workflow_transitions", "stage")
