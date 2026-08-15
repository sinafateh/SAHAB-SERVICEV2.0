"""add_repair_orders_table

Revision ID: 35acb890def4
Revises: 425c10a8e59e
Create Date: 2026-08-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "35acb890def4"
down_revision: Union[str, Sequence[str], None] = "425c10a8e59e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ۱. ایجاد جدول سفارشات تعمیر
    op.create_table(
        "repair_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracking_code", sa.String(length=20), nullable=False),
        sa.Column("qr_code", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum('ثبت شده', 'در انتظار بررسی فنی', 'در حال عیب‌یابی', 'در انتظار تایید مشتری', 'در حال تعمیر', 'در حال تست', 'کنترل نهایی', 'آماده تحویل', 'تحویل شده', 'مختومه بدون تعمیر', name="order_status", native_enum=False), nullable=False),
        sa.Column("reception_date", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("operator_name", sa.String(length=100), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("panel_id", sa.Integer(), nullable=True),
        sa.Column("sender_name", sa.String(length=100), nullable=True),
        sa.Column("sender_position", sa.String(length=100), nullable=True),
        sa.Column("sender_phone", sa.String(length=20), nullable=True),
        sa.Column("sender_landline", sa.String(length=20), nullable=True),
        sa.Column("delivery_method", sa.Enum('حضوری', 'پیک', 'تیپاکس', 'باربری', 'پست', 'سایر', name="delivery_method", native_enum=False), nullable=True),
        sa.Column("courier_company", sa.String(length=100), nullable=True),
        sa.Column("courier_tracking", sa.String(length=100), nullable=True),
        sa.Column("physical_damages", sa.JSON(), nullable=False),
        sa.Column("physical_description", sa.Text(), nullable=True),
        sa.Column("accessories", sa.JSON(), nullable=False),
        sa.Column("accessories_description", sa.Text(), nullable=True),
        sa.Column("customer_complaint", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("technical_review_date", sa.DateTime(), nullable=True),
        sa.Column("diagnosis_date", sa.DateTime(), nullable=True),
        sa.Column("repair_start_date", sa.DateTime(), nullable=True),
        sa.Column("repair_complete_date", sa.DateTime(), nullable=True),
        sa.Column("final_delivery_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_code"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["panel_id"], ["panels.id"], ondelete="SET NULL")
    )
    
    op.create_index("ix_repair_orders_id", "repair_orders", ["id"], unique=False)
    op.create_index("ix_repair_orders_tracking_code", "repair_orders", ["tracking_code"], unique=True)
    op.create_index("ix_repair_orders_status", "repair_orders", ["status"], unique=False)
    op.create_index("ix_repair_orders_customer_id", "repair_orders", ["customer_id"], unique=False)

def downgrade() -> None:
    op.drop_table("repair_orders")
