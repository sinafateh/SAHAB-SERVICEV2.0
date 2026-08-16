from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TechnicalStageTiming(Base):
    """ثبت زمان اجرای هر نوبت از مراحل فنی پرونده."""

    __tablename__ = "technical_stage_timings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        ForeignKey("repair_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RUNNING", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    repair_order = relationship("RepairOrder")
    user = relationship("User")

    __table_args__ = (
        Index("ix_technical_timing_order_stage_status", "repair_order_id", "stage", "status"),
    )
