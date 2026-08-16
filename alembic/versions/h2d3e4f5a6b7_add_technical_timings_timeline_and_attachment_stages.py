"""add technical timings, case timeline events and attachment stages

Revision ID: h2d3e4f5a6b7
Revises: g1c4e7a9b2d0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "g1c4e7a9b2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "attachments",
        sa.Column("stage", sa.String(length=30), nullable=True, server_default="GENERAL"),
    )
    op.execute("UPDATE attachments SET stage = 'GENERAL' WHERE stage IS NULL")
    op.alter_column("attachments", "stage", nullable=False, server_default="GENERAL")

    op.create_table(
        "technical_stage_timings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_order_id", sa.Integer(), sa.ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RUNNING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_technical_stage_timings_id", "technical_stage_timings", ["id"])
    op.create_index("ix_technical_stage_timings_repair_order_id", "technical_stage_timings", ["repair_order_id"])
    op.create_index("ix_technical_stage_timings_user_id", "technical_stage_timings", ["user_id"])
    op.create_index("ix_technical_stage_timings_stage", "technical_stage_timings", ["stage"])
    op.create_index("ix_technical_stage_timings_status", "technical_stage_timings", ["status"])
    op.create_index(
        "ix_technical_timing_order_stage_status",
        "technical_stage_timings",
        ["repair_order_id", "stage", "status"],
    )

    op.create_table(
        "case_timeline_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_order_id", sa.Integer(), sa.ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stage", sa.String(length=50), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_case_timeline_events_id", "case_timeline_events", ["id"])
    op.create_index("ix_case_timeline_events_repair_order_id", "case_timeline_events", ["repair_order_id"])
    op.create_index("ix_case_timeline_events_actor_id", "case_timeline_events", ["actor_id"])
    op.create_index("ix_case_timeline_events_event_type", "case_timeline_events", ["event_type"])
    op.create_index("ix_case_timeline_events_stage", "case_timeline_events", ["stage"])
    op.create_index("ix_case_timeline_events_created_at", "case_timeline_events", ["created_at"])
    op.create_index("ix_case_timeline_order_created", "case_timeline_events", ["repair_order_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_case_timeline_order_created", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_created_at", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_stage", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_event_type", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_actor_id", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_repair_order_id", table_name="case_timeline_events")
    op.drop_index("ix_case_timeline_events_id", table_name="case_timeline_events")
    op.drop_table("case_timeline_events")

    op.drop_index("ix_technical_timing_order_stage_status", table_name="technical_stage_timings")
    op.drop_index("ix_technical_stage_timings_status", table_name="technical_stage_timings")
    op.drop_index("ix_technical_stage_timings_stage", table_name="technical_stage_timings")
    op.drop_index("ix_technical_stage_timings_user_id", table_name="technical_stage_timings")
    op.drop_index("ix_technical_stage_timings_repair_order_id", table_name="technical_stage_timings")
    op.drop_index("ix_technical_stage_timings_id", table_name="technical_stage_timings")
    op.drop_table("technical_stage_timings")
    op.drop_column("attachments", "stage")
