"""add_workflow_transitions

Revision ID: 14dbb8904c17
Revises: 425c10a8e59e
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "14dbb8904c17"
down_revision: Union[str, Sequence[str], None] = "35acb890def4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_transitions",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column("repair_order_id", sa.Integer(), nullable=False),

        sa.Column("from_user_id", sa.Integer(), nullable=True),
        sa.Column("to_user_id", sa.Integer(), nullable=False),

        sa.Column("from_department", sa.String(length=100), nullable=True),
        sa.Column("to_department", sa.String(length=100), nullable=False),

        sa.Column("action", sa.String(length=100), nullable=False, server_default="transfer"),
        sa.Column("note", sa.Text(), nullable=True),

        sa.Column("is_received", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("received_at", sa.DateTime(), nullable=True),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),

        sa.ForeignKeyConstraint(
            ["repair_order_id"],
            ["repair_orders.id"],
            ondelete="CASCADE",
            name="fk_workflow_transitions_repair_order_id",
        ),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_workflow_transitions_from_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["to_user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_workflow_transitions_to_user_id",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_workflow_transitions_id",
        "workflow_transitions",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_workflow_transitions_repair_order_id",
        "workflow_transitions",
        ["repair_order_id"],
        unique=False,
    )

    op.create_index(
        "ix_workflow_transitions_from_user_id",
        "workflow_transitions",
        ["from_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_workflow_transitions_to_user_id",
        "workflow_transitions",
        ["to_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_workflow_transitions_is_received",
        "workflow_transitions",
        ["is_received"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_transitions_is_received", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_to_user_id", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_from_user_id", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_repair_order_id", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_id", table_name="workflow_transitions")

    op.drop_table("workflow_transitions")
