from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RepairDiagnosisReport(Base):
    """گزارش حرفه‌ای عیب‌یابی فعلی پرونده."""

    __tablename__ = "repair_diagnosis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repair_order_id: Mapped[int] = mapped_column(
        ForeignKey("repair_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    technician_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    symptom_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repair_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_duration_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    duration_tolerance_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    confidence_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    repair_order = relationship("RepairOrder")
    technician = relationship("User", foreign_keys=[technician_id])
    parts = relationship(
        "RepairDiagnosisPart",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="RepairDiagnosisPart.id",
    )
    revisions = relationship(
        "RepairDiagnosisRevision",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="RepairDiagnosisRevision.version.desc()",
    )


class RepairDiagnosisPart(Base):
    """قطعه یا قلم موردنیاز ثبت‌شده در گزارش عیب‌یابی."""

    __tablename__ = "repair_diagnosis_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("repair_diagnosis_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part_name: Mapped[str] = mapped_column(String(255), nullable=False)
    part_number: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    price_tolerance_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    price_source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    availability: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report = relationship("RepairDiagnosisReport", back_populates="parts")


class RepairDiagnosisRevision(Base):
    """نسخه‌های قبلی گزارش برای جلوگیری از ازبین‌رفتن تاریخچه و دوباره‌کاری."""

    __tablename__ = "repair_diagnosis_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("repair_diagnosis_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    report = relationship("RepairDiagnosisReport", back_populates="revisions")
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])

    __table_args__ = (
        UniqueConstraint("report_id", "version", name="uq_diagnosis_revision_report_version"),
        Index("ix_diagnosis_revision_report_created", "report_id", "created_at"),
    )
