"""add user departments, workflow state, and notifications

Revision ID: f6b0a8d2e4c1
Revises: b90da6a9cb86
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6b0a8d2e4c1"
down_revision: Union[str, Sequence[str], None] = "b90da6a9cb86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    def columns(table: str) -> set[str]:
        return {column["name"] for column in inspector.get_columns(table)}

    def indexes(table: str) -> set[str]:
        return {index["name"] for index in inspector.get_indexes(table)}

    def foreign_keys(table: str) -> set[str]:
        return {fk.get("name") for fk in inspector.get_foreign_keys(table)}

    def add_column(table: str, column: sa.Column) -> None:
        if column.name not in columns(table):
            op.add_column(table, column)

    def create_index(name: str, table: str, fields: list[str]) -> None:
        if name not in indexes(table):
            op.create_index(name, table, fields, unique=False)

    add_column("users", sa.Column("department", sa.String(length=50), nullable=True))
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
    create_index("ix_users_department", "users", ["department"])
    create_index("ix_users_department_active", "users", ["department", "is_active"])

    add_column(
        "repair_orders",
        sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="RECEPTION_INTAKE"),
    )
    add_column("repair_orders", sa.Column("current_user_id", sa.Integer(), nullable=True))
    add_column("repair_orders", sa.Column("diagnosis_notes", sa.Text(), nullable=True))
    add_column("repair_orders", sa.Column("repair_notes", sa.Text(), nullable=True))
    add_column("repair_orders", sa.Column("final_test_notes", sa.Text(), nullable=True))
    add_column("repair_orders", sa.Column("quoted_price", sa.Numeric(14, 2), nullable=True))
    add_column("repair_orders", sa.Column("price_notes", sa.Text(), nullable=True))
    add_column("repair_orders", sa.Column("customer_approval", sa.String(length=20), nullable=True))
    add_column("repair_orders", sa.Column("customer_approval_note", sa.Text(), nullable=True))
    add_column("repair_orders", sa.Column("price_decided_at", sa.DateTime(), nullable=True))
    add_column("repair_orders", sa.Column("customer_response_at", sa.DateTime(), nullable=True))
    add_column("repair_orders", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    create_index("ix_repair_orders_current_stage", "repair_orders", ["current_stage"])
    create_index("ix_repair_orders_current_user_id", "repair_orders", ["current_user_id"])
    if "fk_repair_orders_current_user_id" not in foreign_keys("repair_orders"):
        op.create_foreign_key(
            "fk_repair_orders_current_user_id",
            "repair_orders",
            "users",
            ["current_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    add_column("workflow_transitions", sa.Column("rejection_reason", sa.Text(), nullable=True))
    add_column("workflow_transitions", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    create_index("ix_workflow_transitions_status", "workflow_transitions", ["status"])
    create_index(
        "ix_workflow_transitions_order_status",
        "workflow_transitions",
        ["repair_order_id", "status"],
    )

    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("notification_type", sa.String(length=80), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("repair_order_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["repair_order_id"], ["repair_orders.id"], ondelete="CASCADE"),
        )
    else:
        add_column("notifications", sa.Column("notification_type", sa.String(length=80), nullable=True))

    create_index("ix_notifications_user_id", "notifications", ["user_id"])
    create_index("ix_notifications_is_read", "notifications", ["is_read"])
    create_index("ix_notifications_repair_order_id", "notifications", ["repair_order_id"])
    create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    # The migration is intentionally tolerant of pre-existing local additions.
    # Rollback is kept conservative so it does not remove columns owned by an
    # earlier local migration.
    pass
