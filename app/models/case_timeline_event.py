from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CaseTimelineEvent(Base):
    """رویدادهای قابل نمایش در تایم‌لاین تصویری پرونده."""

    __tablename__ = "case_timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        ForeignKey("repair_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    repair_order = relationship("RepairOrder")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_case_timeline_order_created", "repair_order_id", "created_at"),
    )
