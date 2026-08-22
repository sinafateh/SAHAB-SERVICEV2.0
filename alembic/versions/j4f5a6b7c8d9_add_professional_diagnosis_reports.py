"""add professional diagnosis reports and revision history

Revision ID: j4f5a6b7c8d9
Revises: i3f4a5b6c7d8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "i3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    def create_if_missing(name: str, *columns, **kwargs) -> None:
        inspector = sa.inspect(bind)
        if name not in inspector.get_table_names():
            op.create_table(name, *columns, **kwargs)

    create_if_missing(
        "repair_diagnosis_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repair_order_id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("symptom_summary", sa.Text(), nullable=True),
        sa.Column("diagnostic_method", sa.Text(), nullable=True),
        sa.Column("tests_performed", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("risk_assessment", sa.Text(), nullable=True),
        sa.Column("repair_scope", sa.Text(), nullable=True),
        sa.Column("repair_recommendation", sa.Text(), nullable=True),
        sa.Column("labor_notes", sa.Text(), nullable=True),
        sa.Column("customer_impact", sa.Text(), nullable=True),
        sa.Column("estimated_duration_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("duration_tolerance_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("confidence_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repair_order_id"], ["repair_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["technician_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("repair_order_id", name="uq_diagnosis_report_order"),
    )
    create_if_missing(
        "repair_diagnosis_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("part_name", sa.String(length=255), nullable=False),
        sa.Column("part_number", sa.String(length=150), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("price_tolerance_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("price_source_url", sa.String(length=1000), nullable=True),
        sa.Column("availability", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_id"], ["repair_diagnosis_reports.id"], ondelete="CASCADE"),
    )
    create_if_missing(
        "repair_diagnosis_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("change_summary", sa.String(length=500), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_id"], ["repair_diagnosis_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("report_id", "version", name="uq_diagnosis_revision_report_version"),
    )

    index_specs = [
        ("ix_repair_diagnosis_reports_id", "repair_diagnosis_reports", ["id"]),
        ("ix_repair_diagnosis_reports_repair_order_id", "repair_diagnosis_reports", ["repair_order_id"]),
        ("ix_repair_diagnosis_reports_technician_id", "repair_diagnosis_reports", ["technician_id"]),
        ("ix_repair_diagnosis_reports_status", "repair_diagnosis_reports", ["status"]),
        ("ix_repair_diagnosis_parts_id", "repair_diagnosis_parts", ["id"]),
        ("ix_repair_diagnosis_parts_report_id", "repair_diagnosis_parts", ["report_id"]),
        ("ix_repair_diagnosis_revisions_id", "repair_diagnosis_revisions", ["id"]),
        ("ix_repair_diagnosis_revisions_report_id", "repair_diagnosis_revisions", ["report_id"]),
        ("ix_repair_diagnosis_revisions_changed_by_user_id", "repair_diagnosis_revisions", ["changed_by_user_id"]),
        ("ix_repair_diagnosis_revisions_created_at", "repair_diagnosis_revisions", ["created_at"]),
        ("ix_diagnosis_revision_report_created", "repair_diagnosis_revisions", ["report_id", "created_at"]),
    ]
    for name, table, columns in index_specs:
        if name not in {item["name"] for item in sa.inspect(bind).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade() -> None:
    op.drop_index("ix_diagnosis_revision_report_created", table_name="repair_diagnosis_revisions")
    op.drop_index("ix_repair_diagnosis_revisions_created_at", table_name="repair_diagnosis_revisions")
    op.drop_index("ix_repair_diagnosis_revisions_changed_by_user_id", table_name="repair_diagnosis_revisions")
    op.drop_index("ix_repair_diagnosis_revisions_report_id", table_name="repair_diagnosis_revisions")
    op.drop_index("ix_repair_diagnosis_revisions_id", table_name="repair_diagnosis_revisions")
    op.drop_table("repair_diagnosis_revisions")
    op.drop_index("ix_repair_diagnosis_parts_report_id", table_name="repair_diagnosis_parts")
    op.drop_index("ix_repair_diagnosis_parts_id", table_name="repair_diagnosis_parts")
    op.drop_table("repair_diagnosis_parts")
    op.drop_index("ix_repair_diagnosis_reports_status", table_name="repair_diagnosis_reports")
    op.drop_index("ix_repair_diagnosis_reports_technician_id", table_name="repair_diagnosis_reports")
    op.drop_index("ix_repair_diagnosis_reports_repair_order_id", table_name="repair_diagnosis_reports")
    op.drop_index("ix_repair_diagnosis_reports_id", table_name="repair_diagnosis_reports")
    op.drop_table("repair_diagnosis_reports")
