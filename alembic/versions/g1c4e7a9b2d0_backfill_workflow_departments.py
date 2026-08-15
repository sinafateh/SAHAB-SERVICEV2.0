"""backfill workflow departments for existing users

Revision ID: g1c4e7a9b2d0
Revises: f6b0a8d2e4c1
"""

from typing import Sequence, Union

from alembic import op


revision: str = "g1c4e7a9b2d0"
down_revision: Union[str, Sequence[str], None] = "f6b0a8d2e4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET department = CASE role
            WHEN 'RECEPTION' THEN 'RECEPTION'
            WHEN 'TECHNICAL' THEN 'TECHNICAL'
            WHEN 'CUSTOMER_RELATIONS' THEN 'CUSTOMER_RELATIONS'
            WHEN 'MANAGEMENT' THEN 'MANAGEMENT'
            ELSE department
        END
        WHERE department IS NULL
        """
    )


def downgrade() -> None:
    pass
