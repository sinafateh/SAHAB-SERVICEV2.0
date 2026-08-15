"""add_workflow_handoff_models

Revision ID: d8e2610201c5
Revises: 28f68e893c13
Create Date: 2026-08-09 08:40:38.233730
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8e2610201c5"
down_revision: Union[str, Sequence[str], None] = "28f68e893c13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RECEIVED_BY_FK = "fk_workflow_transitions_received_by"


def upgrade() -> None:
    """Add fields required for workflow handoff confirmation."""

    # وضعیت انتقال:
    # PENDING  = در انتظار تأیید گیرنده
    # RECEIVED = دریافت‌شده توسط گیرنده
    # REJECTED = ردشده توسط گیرنده
    op.add_column(
        "workflow_transitions",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=True,
        ),
    )

    # مقداردهی رکوردهای قبلی براساس is_received.
    op.execute(
        """
        UPDATE workflow_transitions
        SET status = CASE
            WHEN is_received IS TRUE THEN 'RECEIVED'
            ELSE 'PENDING'
        END
        """
    )

    op.alter_column(
        "workflow_transitions",
        "status",
        existing_type=sa.String(length=20),
        nullable=False,
    )

    # شناسه کاربری که دریافت پرونده را تأیید کرده است.
    op.add_column(
        "workflow_transitions",
        sa.Column(
            "received_by",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        RECEIVED_BY_FK,
        "workflow_transitions",
        "users",
        ["received_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # برای انتقال‌های تأییدشده قدیمی، گیرنده را ثبت می‌کنیم.
    op.execute(
        """
        UPDATE workflow_transitions
        SET received_by = to_user_id
        WHERE is_received IS TRUE
          AND received_by IS NULL
        """
    )

    # یادداشت رویدادهای تاریخچه پرونده.
    # ستون reason قدیمی عمداً حفظ می‌شود تا داده‌ای حذف نشود.
    op.add_column(
        "status_histories",
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove workflow handoff confirmation fields."""

    op.drop_column("status_histories", "note")

    op.drop_constraint(
        RECEIVED_BY_FK,
        "workflow_transitions",
        type_="foreignkey",
    )

    op.drop_column("workflow_transitions", "received_by")
    op.drop_column("workflow_transitions", "status")
