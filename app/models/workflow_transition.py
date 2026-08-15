from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base



class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        ForeignKey("repair_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    from_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    to_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    from_department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    to_department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False, default="transfer")
    stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    repair_order = relationship(
        "RepairOrder",
        back_populates="transitions",
    )

    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])
    received_by_user = relationship("User", foreign_keys=[received_by])

    __table_args__ = (
        Index("ix_workflow_transitions_order_status", "repair_order_id", "status"),
    )
