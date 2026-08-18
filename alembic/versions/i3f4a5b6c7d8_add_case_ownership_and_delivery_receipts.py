"""add case technical ownership and delivery receipt metadata

Revision ID: i3f4a5b6c7d8
Revises: h2d3e4f5a6b7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "h2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def columns(table: str) -> set[str]:
        return {item["name"] for item in inspector.get_columns(table)}

    def add_column(table: str, column: sa.Column) -> None:
        if column.name not in columns(table):
            op.add_column(table, column)

    add_column("attachments", sa.Column("uploaded_by_name", sa.String(length=100), nullable=True))
    add_column("attachments", sa.Column("uploaded_by_department", sa.String(length=50), nullable=True))
    add_column(
        "attachments",
        sa.Column("is_delivery_receipt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    add_column("repair_orders", sa.Column("diagnosed_by_user_id", sa.Integer(), nullable=True))
    add_column("repair_orders", sa.Column("repaired_by_user_id", sa.Integer(), nullable=True))
    add_column("repair_orders", sa.Column("final_tested_by_user_id", sa.Integer(), nullable=True))

    existing_fks = {item.get("name") for item in inspector.get_foreign_keys("repair_orders")}
    for name, column in (
        ("fk_repair_orders_diagnosed_by_user_id", "diagnosed_by_user_id"),
        ("fk_repair_orders_repaired_by_user_id", "repaired_by_user_id"),
        ("fk_repair_orders_final_tested_by_user_id", "final_tested_by_user_id"),
    ):
        if name not in existing_fks:
            op.create_foreign_key(
                name,
                "repair_orders",
                "users",
                [column],
                ["id"],
                ondelete="SET NULL",
            )

    existing_indexes = {item["name"] for item in inspector.get_indexes("repair_orders")}
    for name, column in (
        ("ix_repair_orders_diagnosed_by_user_id", "diagnosed_by_user_id"),
        ("ix_repair_orders_repaired_by_user_id", "repaired_by_user_id"),
        ("ix_repair_orders_final_tested_by_user_id", "final_tested_by_user_id"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "repair_orders", [column])


def downgrade() -> None:
    op.drop_index("ix_repair_orders_final_tested_by_user_id", table_name="repair_orders")
    op.drop_index("ix_repair_orders_repaired_by_user_id", table_name="repair_orders")
    op.drop_index("ix_repair_orders_diagnosed_by_user_id", table_name="repair_orders")
    op.drop_constraint("fk_repair_orders_final_tested_by_user_id", "repair_orders", type_="foreignkey")
    op.drop_constraint("fk_repair_orders_repaired_by_user_id", "repair_orders", type_="foreignkey")
    op.drop_constraint("fk_repair_orders_diagnosed_by_user_id", "repair_orders", type_="foreignkey")
    op.drop_column("repair_orders", "final_tested_by_user_id")
    op.drop_column("repair_orders", "repaired_by_user_id")
    op.drop_column("repair_orders", "diagnosed_by_user_id")
    op.drop_column("attachments", "is_delivery_receipt")
    op.drop_column("attachments", "uploaded_by_department")
    op.drop_column("attachments", "uploaded_by_name")
