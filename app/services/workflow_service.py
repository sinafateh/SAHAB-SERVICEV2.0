from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import PRIVILEGED_ROLES
from app.models.attachment import Attachment
from app.models.diagnosis import RepairDiagnosisPart, RepairDiagnosisReport, RepairDiagnosisRevision
from app.models.notification import Notification
from app.models.case_timeline_event import CaseTimelineEvent
from app.models.repair_order import OrderStatus, RepairOrder
from app.models.status_history import StatusHistory
from app.models.technical_stage_timing import TechnicalStageTiming
from app.models.user import User
from app.models.workflow_transition import WorkflowTransition


DEPARTMENTS = {
    "RECEPTION": "پذیرش",
    "TECHNICAL": "فنی",
    "MANAGEMENT": "مدیریت",
    "CUSTOMER_RELATIONS": "ارتباط با مشتریان",
}

STAGES = {
    "RECEPTION_INTAKE": {
        "label": "پذیرش و تشکیل پرونده",
        "department": "RECEPTION",
        "status": OrderStatus.REGISTERED,
    },
    "TECHNICAL_DIAGNOSIS": {
        "label": "عیب‌یابی فنی",
        "department": "TECHNICAL",
        "status": OrderStatus.DIAGNOSING,
    },
    "MANAGEMENT_PRICING": {
        "label": "تعیین قیمت مدیریت",
        "department": "MANAGEMENT",
        "status": OrderStatus.WAITING_APPROVAL,
    },
    "CUSTOMER_APPROVAL": {
        "label": "اعلام نظر مشتری",
        "department": "CUSTOMER_RELATIONS",
        "status": OrderStatus.WAITING_APPROVAL,
    },
    "TECHNICAL_REPAIR": {
        "label": "تعمیر فنی",
        "department": "TECHNICAL",
        "status": OrderStatus.REPAIRING,
    },
    "TECHNICAL_FINAL_TEST": {
        "label": "تست نهایی فنی",
        "department": "TECHNICAL",
        "status": OrderStatus.FINAL_CONTROL,
    },
    "RECEPTION_DELIVERY": {
        "label": "هماهنگی و تحویل",
        "department": "RECEPTION",
        "status": OrderStatus.READY_DELIVERY,
    },
}

ROLE_DEPARTMENT = {
    "RECEPTION": "RECEPTION",
    "CUSTOMER_RELATIONS": "CUSTOMER_RELATIONS",
    "TECHNICAL": "TECHNICAL",
    "MANAGEMENT": "MANAGEMENT",
}

TECHNICAL_TIMED_STAGES = {
    "TECHNICAL_DIAGNOSIS",
    "TECHNICAL_REPAIR",
    "TECHNICAL_FINAL_TEST",
}
TERMINAL_STAGES = {"COMPLETED", "CLOSED_NO_REPAIR"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowService:
    @staticmethod
    def ensure_case_editable(order: RepairOrder, current_user: User) -> None:
        if (
            order.current_stage in TERMINAL_STAGES
            or order.status in {OrderStatus.DELIVERED, OrderStatus.CLOSED_NO_REPAIR}
        ) and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="پرونده مختومه است و فقط مدیریت می‌تواند آن را تغییر دهد.",
            )

    @staticmethod
    def ensure_diagnosis_edit_access(order: RepairOrder, current_user: User) -> None:
        WorkflowService.ensure_case_editable(order, current_user)
        if current_user.role in PRIVILEGED_ROLES:
            return
        if WorkflowService.effective_department(current_user) != "TECHNICAL":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="گزارش عیب‌یابی فقط برای کاربران بخش فنی قابل ثبت است.",
            )
        if order.current_stage != "TECHNICAL_DIAGNOSIS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="گزارش عیب‌یابی فقط در مرحله عیب‌یابی قابل تکمیل است.",
            )
        if order.current_user_id and order.current_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="این پرونده در اختیار تکنسین دیگری است.",
            )

    @staticmethod
    def _diagnosis_snapshot(report: RepairDiagnosisReport) -> dict[str, Any]:
        def value(item: Any) -> Any:
            if isinstance(item, Decimal):
                return str(item)
            if isinstance(item, datetime):
                return item.isoformat()
            return item

        fields = (
            "status",
            "version",
            "symptom_summary",
            "findings",
            "root_cause",
            "repair_scope",
            "estimated_duration_hours",
            "duration_tolerance_percent",
            "confidence_percent",
            "submitted_at",
        )
        snapshot = {
            field: value(getattr(report, field))
            for field in fields
        }
        snapshot["parts"] = [
            {
                "part_name": part.part_name,
                "part_number": part.part_number,
                "quantity": value(part.quantity),
                "unit_price": value(part.unit_price),
                "price_tolerance_percent": value(part.price_tolerance_percent),
                "price_source_url": part.price_source_url,
                "availability": part.availability,
                "notes": part.notes,
            }
            for part in report.parts
        ]
        return snapshot

    @staticmethod
    def diagnosis_report_response(
        report: Optional[RepairDiagnosisReport],
        order: RepairOrder,
        current_user: User,
    ) -> dict[str, Any]:
        can_edit = False
        if report is not None:
            can_edit = current_user.role in PRIVILEGED_ROLES or (
                WorkflowService.effective_department(current_user) == "TECHNICAL"
                and order.current_stage == "TECHNICAL_DIAGNOSIS"
                and (not order.current_user_id or order.current_user_id == current_user.id)
            )
        revisions = []
        if report:
            revisions = [
                {
                    "id": item.id,
                    "version": item.version,
                    "changed_by_user_id": item.changed_by_user_id,
                    "changed_by_name": item.changed_by.full_name if item.changed_by else None,
                    "change_summary": item.change_summary,
                    "created_at": item.created_at,
                    "snapshot": item.snapshot,
                }
                for item in report.revisions
            ]
        if not report:
            return {
                "report": None,
                "revisions": [],
                "can_edit": current_user.role in PRIVILEGED_ROLES or (
                    WorkflowService.effective_department(current_user) == "TECHNICAL"
                    and order.current_stage == "TECHNICAL_DIAGNOSIS"
                    and (not order.current_user_id or order.current_user_id == current_user.id)
                ),
                "current_stage": order.current_stage,
                "customer_complaint": order.customer_complaint,
            }
        return {
            "report": {
                "id": report.id,
                "repair_order_id": report.repair_order_id,
                "technician_id": report.technician_id,
                "technician_name": report.technician.full_name if report.technician else None,
                "customer_complaint": order.customer_complaint,
                "status": report.status,
                "version": report.version,
                "symptom_summary": report.symptom_summary,
                "findings": report.findings,
                "root_cause": report.root_cause,
                "repair_scope": report.repair_scope,
                "estimated_duration_hours": report.estimated_duration_hours,
                "duration_tolerance_percent": report.duration_tolerance_percent,
                "confidence_percent": report.confidence_percent,
                "submitted_at": report.submitted_at,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
                "parts": [
                    {
                        "id": part.id,
                        "part_name": part.part_name,
                        "part_number": part.part_number,
                        "quantity": part.quantity,
                        "unit_price": part.unit_price,
                        "price_tolerance_percent": part.price_tolerance_percent,
                        "price_source_url": part.price_source_url,
                        "availability": part.availability,
                        "notes": part.notes,
                    }
                    for part in report.parts
                ],
            },
            "revisions": revisions,
            "can_edit": can_edit,
            "current_stage": order.current_stage,
        }

    @staticmethod
    def get_diagnosis_report(
        db: Session,
        order: RepairOrder,
        current_user: User,
    ) -> dict[str, Any]:
        report = (
            db.query(RepairDiagnosisReport)
            .options(
                joinedload(RepairDiagnosisReport.technician),
                selectinload(RepairDiagnosisReport.parts),
                selectinload(RepairDiagnosisReport.revisions).joinedload(
                    RepairDiagnosisRevision.changed_by
                ),
            )
            .filter(RepairDiagnosisReport.repair_order_id == order.id)
            .first()
        )
        return WorkflowService.diagnosis_report_response(report, order, current_user)

    @staticmethod
    def save_diagnosis_report(
        db: Session,
        order: RepairOrder,
        current_user: User,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        WorkflowService.ensure_diagnosis_edit_access(order, current_user)
        report = (
            db.query(RepairDiagnosisReport)
            .options(selectinload(RepairDiagnosisReport.parts))
            .filter(RepairDiagnosisReport.repair_order_id == order.id)
            .first()
        )
        if report is None:
            report = RepairDiagnosisReport(
                repair_order_id=order.id,
                technician_id=order.current_user_id or current_user.id,
                version=0,
            )
            db.add(report)
            db.flush()

        report.version = int(report.version or 0) + 1
        report.status = "SUBMITTED" if data.get("submit") else "DRAFT"
        report.technician_id = report.technician_id or order.current_user_id or current_user.id
        for field in (
            "findings",
            "root_cause",
            "repair_scope",
            "estimated_duration_hours",
            "duration_tolerance_percent",
            "confidence_percent",
        ):
            setattr(report, field, data.get(field))
        report.symptom_summary = order.customer_complaint or report.symptom_summary
        report.submitted_at = utc_now() if data.get("submit") else None

        report.parts.clear()
        for item in data.get("parts") or []:
            part_data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            report.parts.append(RepairDiagnosisPart(**part_data))

        db.flush()
        snapshot = WorkflowService._diagnosis_snapshot(report)
        revision = RepairDiagnosisRevision(
            report_id=report.id,
            version=report.version,
            changed_by_user_id=current_user.id,
            change_summary=data.get("change_summary") or (
                "گزارش عیب‌یابی برای ادامه فرآیند ثبت شد."
                if data.get("submit")
                else "پیش‌نویس گزارش عیب‌یابی ذخیره شد."
            ),
            snapshot=snapshot,
        )
        db.add(revision)
        if data.get("submit"):
            order.diagnosis_notes = report.findings
        WorkflowService.add_timeline_event(
            db,
            order,
            current_user,
            "DIAGNOSIS_REPORT_SUBMITTED" if data.get("submit") else "DIAGNOSIS_REPORT_SAVED",
            "ثبت گزارش حرفه‌ای عیب‌یابی",
            revision.change_summary,
            "TECHNICAL_DIAGNOSIS",
            {"report_id": report.id, "version": report.version, "status": report.status},
        )
        db.commit()
        db.refresh(order)
        return WorkflowService.get_diagnosis_report(db, order, current_user)

    @staticmethod
    def effective_department(user: User) -> Optional[str]:
        return getattr(user, "department", None) or ROLE_DEPARTMENT.get(user.role)

    @staticmethod
    def get_order(db: Session, repair_order_id: int) -> RepairOrder:
        order = (
            db.query(RepairOrder)
            .options(joinedload(RepairOrder.current_user))
            .filter(RepairOrder.id == repair_order_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پرونده پیدا نشد")
        return order

    @staticmethod
    def get_user(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کاربر مقصد پیدا نشد")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="کاربر مقصد غیرفعال است")
        return user

    @staticmethod
    def validate_stage(stage: str) -> dict:
        config = STAGES.get(stage)
        if not config:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مرحله‌ی workflow معتبر نیست")
        return config

    @staticmethod
    def validate_recipient(db: Session, to_user_id: int, stage: str, to_department: Optional[str]) -> tuple[User, str]:
        config = WorkflowService.validate_stage(stage)
        recipient = WorkflowService.get_user(db, to_user_id)
        department = WorkflowService.effective_department(recipient)
        requested_department = to_department or department

        if recipient.role not in PRIVILEGED_ROLES and requested_department != config["department"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"گیرنده باید از بخش {DEPARTMENTS[config['department']]} باشد",
            )
        if recipient.role not in PRIVILEGED_ROLES and department != config["department"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="بخش کاربر مقصد با مرحله‌ی انتخاب‌شده سازگار نیست",
            )
        return recipient, requested_department

    @staticmethod
    def ensure_sender_can_transfer(order: RepairOrder, current_user: User) -> None:
        WorkflowService.ensure_case_editable(order, current_user)
        if current_user.role in PRIVILEGED_ROLES:
            return
        if order.current_user_id and order.current_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="این پرونده در اختیار کاربر دیگری است",
            )
        department = WorkflowService.effective_department(current_user)
        if department not in DEPARTMENTS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="این کاربر مجاز به انتقال پرونده نیست")

    @staticmethod
    def pending_transition(db: Session, repair_order_id: int) -> Optional[WorkflowTransition]:
        return (
            db.query(WorkflowTransition)
            .filter(
                WorkflowTransition.repair_order_id == repair_order_id,
                WorkflowTransition.status == "PENDING",
            )
            .order_by(WorkflowTransition.created_at.desc())
            .first()
        )

    @staticmethod
    def add_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        repair_order_id: int,
    ) -> None:
        db.add(
            Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                repair_order_id=repair_order_id,
            )
        )

    @staticmethod
    def add_history(
        db: Session,
        order: RepairOrder,
        actor: User,
        old_status: Optional[OrderStatus],
        new_status: OrderStatus,
        note: str,
    ) -> None:
        db.add(
            StatusHistory(
                repair_order_id=order.id,
                old_status=old_status,
                new_status=new_status,
                reason=note,
                note=note,
                operator_name=actor.full_name,
                changed_by=actor.id,
                changed_at=utc_now(),
            )
        )

    @staticmethod
    def add_timeline_event(
        db: Session,
        order: RepairOrder,
        actor: Optional[User],
        event_type: str,
        title: str,
        description: Optional[str] = None,
        stage: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        db.add(
            CaseTimelineEvent(
                repair_order_id=order.id,
                actor_id=actor.id if actor else None,
                event_type=event_type,
                title=title,
                description=description,
                stage=stage or order.current_stage,
                metadata_json=metadata,
                created_at=utc_now(),
            )
        )

    @staticmethod
    def transfer_order(
        db: Session,
        order: RepairOrder,
        current_user: User,
        to_user_id: int,
        stage: str,
        to_department: Optional[str] = None,
        note: Optional[str] = None,
    ) -> WorkflowTransition:
        WorkflowService.ensure_sender_can_transfer(order, current_user)
        recipient, department = WorkflowService.validate_recipient(db, to_user_id, stage, to_department)

        if recipient.id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="انتقال به خود کاربر مجاز نیست")
        if stage == "TECHNICAL_REPAIR":
            if not order.diagnosed_by_user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="ابتدا باید عیب‌یابی توسط یک تکنسین ثبت شود.",
                )
            if recipient.id != order.diagnosed_by_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تعمیر باید به همان تکنسینی ارجاع شود که عیب‌یابی را انجام داده است.",
                )
        if stage == "TECHNICAL_FINAL_TEST":
            prohibited_ids = {
                item
                for item in (order.diagnosed_by_user_id, order.repaired_by_user_id, current_user.id)
                if item
            }
            if recipient.id in prohibited_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تست نهایی باید توسط تکنسینی غیر از عیب‌یاب و تعمیرکار انجام شود.",
                )
        if WorkflowService.pending_transition(db, order.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="برای این پرونده یک انتقال باز وجود دارد")

        transition = WorkflowTransition(
            repair_order_id=order.id,
            from_user_id=current_user.id,
            to_user_id=recipient.id,
            from_department=WorkflowService.effective_department(current_user),
            to_department=department,
            action="TRANSFER",
            stage=stage,
            note=note,
            status="PENDING",
            is_received=False,
        )
        db.add(transition)
        WorkflowService.add_notification(
            db,
            recipient.id,
            "درخواست دریافت پرونده",
            f"پرونده {order.tracking_code} برای مرحله «{STAGES[stage]['label']}» به شما ارجاع شده است.",
            "WORKFLOW_TRANSFER",
            order.id,
        )
        WorkflowService.add_timeline_event(
            db,
            order,
            current_user,
            "TRANSFER_REQUESTED",
            "درخواست انتقال پرونده",
            f"پرونده برای مرحله «{STAGES[stage]['label']}» به {recipient.full_name} ارجاع شد.",
            stage,
            {"to_user_id": recipient.id, "to_user_name": recipient.full_name},
        )
        db.commit()
        db.refresh(transition)
        return transition

    @staticmethod
    def get_my_tasks(db: Session, current_user_id: int) -> list[WorkflowTransition]:
        return (
            db.query(WorkflowTransition)
            .options(joinedload(WorkflowTransition.from_user), joinedload(WorkflowTransition.to_user))
            .filter(
                WorkflowTransition.to_user_id == current_user_id,
                WorkflowTransition.status == "PENDING",
            )
            .order_by(WorkflowTransition.created_at.asc())
            .all()
        )

    @staticmethod
    def receive_transition(db: Session, transition_id: int, current_user: User) -> WorkflowTransition:
        transition = (
            db.query(WorkflowTransition)
            .options(joinedload(WorkflowTransition.repair_order))
            .filter(WorkflowTransition.id == transition_id)
            .first()
        )
        if not transition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="درخواست انتقال پیدا نشد")
        if transition.to_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="شما گیرنده‌ی این انتقال نیستید")
        if transition.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این درخواست قبلاً تعیین تکلیف شده است")

        order = transition.repair_order
        WorkflowService.ensure_case_editable(order, current_user)
        old_status = order.status
        config = WorkflowService.validate_stage(transition.stage or "RECEPTION_INTAKE")
        transition.status = "RECEIVED"
        transition.is_received = True
        transition.received_by = current_user.id
        transition.received_at = utc_now()
        order.current_stage = transition.stage
        order.current_user_id = current_user.id
        order.status = config["status"]
        if transition.stage == "TECHNICAL_DIAGNOSIS":
            order.technical_review_date = utc_now()
        elif transition.stage == "TECHNICAL_REPAIR":
            order.repair_start_date = utc_now()
        elif transition.stage == "RECEPTION_DELIVERY":
            order.repair_complete_date = order.repair_complete_date or utc_now()

        WorkflowService.add_history(
            db,
            order,
            current_user,
            old_status,
            order.status,
            f"پرونده توسط {current_user.full_name} دریافت شد؛ مرحله: {config['label']}",
        )
        WorkflowService.add_notification(
            db,
            transition.from_user_id,
            "دریافت پرونده تأیید شد",
            f"پرونده {order.tracking_code} توسط {current_user.full_name} دریافت شد.",
            "WORKFLOW_RECEIVED",
            order.id,
        )
        WorkflowService.add_timeline_event(
            db,
            order,
            current_user,
            "TRANSFER_RECEIVED",
            "دریافت پرونده",
            f"{current_user.full_name} پرونده را برای مرحله «{config['label']}» دریافت کرد.",
            transition.stage,
            {"transition_id": transition.id},
        )
        db.commit()
        db.refresh(transition)
        return transition

    @staticmethod
    def reject_transition(
        db: Session,
        transition_id: int,
        current_user: User,
        reason: str,
    ) -> WorkflowTransition:
        transition = db.query(WorkflowTransition).filter(WorkflowTransition.id == transition_id).first()
        if not transition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="درخواست انتقال پیدا نشد")
        if transition.to_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="شما گیرنده‌ی این انتقال نیستید")
        if transition.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این درخواست قبلاً تعیین تکلیف شده است")

        transition.status = "REJECTED"
        transition.rejection_reason = reason
        transition.rejected_at = utc_now()
        WorkflowService.add_notification(
            db,
            transition.from_user_id,
            "درخواست انتقال رد شد",
            f"درخواست دریافت پرونده توسط {current_user.full_name} رد شد: {reason}",
            "WORKFLOW_REJECTED",
            transition.repair_order_id,
        )
        order = transition.repair_order
        WorkflowService.ensure_case_editable(order, current_user)
        WorkflowService.add_timeline_event(
            db,
            order,
            current_user,
            "TRANSFER_REJECTED",
            "رد دریافت پرونده",
            reason,
            transition.stage,
            {"transition_id": transition.id},
        )
        db.commit()
        db.refresh(transition)
        return transition

    @staticmethod
    def change_recipient(
        db: Session,
        transition_id: int,
        current_user: User,
        to_user_id: int,
        to_department: Optional[str] = None,
    ) -> WorkflowTransition:
        transition = db.query(WorkflowTransition).filter(WorkflowTransition.id == transition_id).first()
        if not transition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="درخواست انتقال پیدا نشد")
        if transition.from_user_id != current_user.id and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط فرستنده می‌تواند گیرنده را تغییر دهد")
        if transition.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="فقط انتقال باز قابل تغییر است")
        WorkflowService.ensure_case_editable(transition.repair_order, current_user)

        recipient, department = WorkflowService.validate_recipient(
            db, to_user_id, transition.stage or "RECEPTION_INTAKE", to_department
        )
        if recipient.id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="انتقال به خود کاربر مجاز نیست")
        transition.to_user_id = recipient.id
        transition.to_department = department
        WorkflowService.add_notification(
            db,
            recipient.id,
            "انتقال پرونده به شما تغییر کرد",
            f"پرونده شماره {transition.repair_order_id} برای دریافت به شما واگذار شده است.",
            "WORKFLOW_TRANSFER",
            transition.repair_order_id,
        )
        order = transition.repair_order
        WorkflowService.add_timeline_event(
            db,
            order,
            current_user,
            "RECIPIENT_CHANGED",
            "تغییر گیرنده انتقال",
            f"گیرنده پرونده به {recipient.full_name} تغییر کرد.",
            transition.stage,
            {"transition_id": transition.id, "to_user_id": recipient.id},
        )
        db.commit()
        db.refresh(transition)
        return transition

    @staticmethod
    def apply_action(
        db: Session,
        order: RepairOrder,
        current_user: User,
        action: str,
        notes: Optional[str] = None,
        quoted_price: Optional[Decimal] = None,
        approved: Optional[bool] = None,
    ) -> RepairOrder:
        WorkflowService.ensure_case_editable(order, current_user)
        if order.current_user_id and order.current_user_id != current_user.id and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="این پرونده در اختیار شما نیست")

        department = WorkflowService.effective_department(current_user)
        action = action.upper()
        now = utc_now()

        if action == "DIAGNOSIS":
            if department != "TECHNICAL":
                raise HTTPException(status_code=403, detail="ثبت عیب‌یابی فقط برای بخش فنی است")
            report = (
                db.query(RepairDiagnosisReport)
                .filter(RepairDiagnosisReport.repair_order_id == order.id)
                .first()
            )
            if not report or report.status != "SUBMITTED":
                raise HTTPException(
                    status_code=400,
                    detail="ابتدا گزارش حرفه‌ای عیب‌یابی را تکمیل و نهایی کنید.",
                )
            if (
                current_user.role not in PRIVILEGED_ROLES
                and report.technician_id
                and report.technician_id != current_user.id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="ثبت نهایی گزارش فقط توسط تکنسین عیب‌یاب انجام می‌شود.",
                )
            order.diagnosis_notes = notes or report.findings
            order.diagnosis_date = now
            order.diagnosed_by_user_id = current_user.id
        elif action == "PRICING":
            if department != "MANAGEMENT":
                raise HTTPException(status_code=403, detail="تعیین قیمت فقط برای مدیریت است")
            if quoted_price is None:
                raise HTTPException(status_code=400, detail="مبلغ پیشنهادی الزامی است")
            order.quoted_price = quoted_price
            order.price_notes = notes
            order.price_decided_at = now
        elif action == "CUSTOMER_DECISION":
            if department not in {"RECEPTION", "CUSTOMER_RELATIONS"}:
                raise HTTPException(status_code=403, detail="ثبت نظر مشتری فقط برای پذیرش یا ارتباط با مشتریان است")
            if approved is None:
                raise HTTPException(status_code=400, detail="تأیید یا عدم تأیید مشتری مشخص نشده است")
            order.customer_approval = "APPROVED" if approved else "REJECTED"
            order.customer_approval_note = notes
            order.customer_response_at = now
            if not approved:
                old_status = order.status
                order.status = OrderStatus.CLOSED_NO_REPAIR
                order.current_stage = "CLOSED_NO_REPAIR"
                WorkflowService.add_history(db, order, current_user, old_status, order.status, "مشتری با قیمت موافقت نکرد")
        elif action == "REPAIR_COMPLETE":
            if department != "TECHNICAL":
                raise HTTPException(status_code=403, detail="ثبت پایان تعمیر فقط برای بخش فنی است")
            order.repair_notes = notes
            order.repair_complete_date = now
            order.repaired_by_user_id = current_user.id
        elif action == "FINAL_TEST":
            if department != "TECHNICAL":
                raise HTTPException(status_code=403, detail="ثبت تست نهایی فقط برای بخش فنی است")
            order.final_test_notes = notes
            if approved is False:
                raise HTTPException(status_code=400, detail="برای تست ناموفق باید پرونده به تعمیر بازگردانده شود")
            if current_user.id in {
                item for item in (order.diagnosed_by_user_id, order.repaired_by_user_id) if item
            }:
                raise HTTPException(
                    status_code=400,
                    detail="تست نهایی باید توسط تکنسینی غیر از عیب‌یاب و تعمیرکار انجام شود.",
                )
            order.status = OrderStatus.FINAL_CONTROL
            order.final_tested_by_user_id = current_user.id
        elif action == "DELIVER":
            if department not in {"RECEPTION", "CUSTOMER_RELATIONS"}:
                raise HTTPException(status_code=403, detail="تحویل فقط برای پذیرش یا ارتباط با مشتریان است")
            receipt = (
                db.query(Attachment)
                .filter(
                    Attachment.repair_order_id == order.id,
                    Attachment.stage == "DELIVERY",
                    Attachment.is_delivery_receipt.is_(True),
                )
                .first()
            )
            if not receipt:
                raise HTTPException(
                    status_code=400,
                    detail="برای مختومه‌کردن پرونده، رسید تحویل مشتری باید ابتدا بارگذاری شود.",
                )
            old_status = order.status
            order.delivered_at = now
            order.final_delivery_date = now
            order.status = OrderStatus.DELIVERED
            order.current_stage = "COMPLETED"
            WorkflowService.add_history(
                db,
                order,
                current_user,
                old_status,
                order.status,
                "پرونده پس از بارگذاری رسید تحویل مشتری بسته شد.",
            )
        else:
            raise HTTPException(status_code=400, detail="عملیات workflow معتبر نیست")

        action_titles = {
            "DIAGNOSIS": "ثبت عیب‌یابی فنی",
            "PRICING": "ثبت قیمت پیشنهادی",
            "CUSTOMER_DECISION": "ثبت تصمیم مشتری",
            "REPAIR_COMPLETE": "ثبت پایان تعمیر",
            "FINAL_TEST": "ثبت نتیجه تست نهایی",
            "DELIVER": "ثبت تحویل دستگاه",
        }
        action_description = notes
        if action == "PRICING" and quoted_price is not None:
            action_description = f"مبلغ پیشنهادی: {quoted_price}"
        elif action == "CUSTOMER_DECISION" and approved is not None:
            action_description = "مشتری موافقت کرد." if approved else "مشتری با قیمت موافقت نکرد."
        WorkflowService.add_timeline_event(
            db, order, current_user, f"ACTION_{action}",
            action_titles.get(action, "ثبت اقدام پرونده"),
            action_description, order.current_stage,
            {
                "action": action,
                "quoted_price": str(quoted_price) if quoted_price is not None else None,
                "approved": approved,
            },
        )
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def _ensure_timing_access(order: RepairOrder, current_user: User, stage: str) -> None:
        WorkflowService.ensure_case_editable(order, current_user)
        if stage not in TECHNICAL_TIMED_STAGES:
            raise HTTPException(status_code=400, detail="Technical timing is only available for technical stages.")
        if order.current_stage != stage:
            raise HTTPException(status_code=409, detail="This stage is not the active stage of the case.")
        if WorkflowService.effective_department(current_user) != "TECHNICAL" and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(status_code=403, detail="Only technical users can record stage timing.")
        if order.current_user_id and order.current_user_id != current_user.id and current_user.role not in PRIVILEGED_ROLES:
            raise HTTPException(status_code=403, detail="This case belongs to another technician.")

    @staticmethod
    def start_timing(db: Session, order: RepairOrder, current_user: User, stage: str, note: Optional[str] = None) -> TechnicalStageTiming:
        WorkflowService._ensure_timing_access(order, current_user, stage)
        running = db.query(TechnicalStageTiming).filter(
            TechnicalStageTiming.repair_order_id == order.id,
            TechnicalStageTiming.stage == stage,
            TechnicalStageTiming.status == "RUNNING",
        ).first()
        if running:
            raise HTTPException(status_code=409, detail="An active timer already exists for this stage.")
        timing = TechnicalStageTiming(
            repair_order_id=order.id,
            user_id=current_user.id,
            stage=stage,
            status="RUNNING",
            started_at=utc_now(),
            note=note,
        )
        db.add(timing)
        db.flush()
        WorkflowService.add_timeline_event(
            db, order, current_user, "TIMING_STARTED",
            "Technical stage timer started",
            f"Timer started for {STAGES[stage]['label']}.",
            stage, {"timing_id": timing.id},
        )
        db.commit()
        db.refresh(timing)
        return timing

    @staticmethod
    def complete_timing(db: Session, order: RepairOrder, current_user: User, stage: str, note: Optional[str] = None) -> TechnicalStageTiming:
        WorkflowService._ensure_timing_access(order, current_user, stage)
        query = db.query(TechnicalStageTiming).filter(
            TechnicalStageTiming.repair_order_id == order.id,
            TechnicalStageTiming.stage == stage,
            TechnicalStageTiming.status == "RUNNING",
        )
        if current_user.role not in PRIVILEGED_ROLES:
            query = query.filter(TechnicalStageTiming.user_id == current_user.id)
        timing = query.order_by(TechnicalStageTiming.started_at.desc()).first()
        if not timing:
            raise HTTPException(status_code=409, detail="No active timer exists for this stage.")
        completed_at = utc_now()
        started_at = timing.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        timing.completed_at = completed_at
        timing.duration_seconds = max(0, int((completed_at - started_at).total_seconds()))
        timing.status = "COMPLETED"
        if note:
            timing.note = f"{timing.note}\n{note}" if timing.note else note
        db.flush()
        WorkflowService.add_timeline_event(
            db, order, current_user, "TIMING_COMPLETED",
            "Technical stage timer completed",
            f"Duration: {timing.duration_seconds} seconds.",
            stage, {"timing_id": timing.id, "duration_seconds": timing.duration_seconds},
        )
        db.commit()
        db.refresh(timing)
        return timing

    @staticmethod
    def get_timings(db: Session, repair_order_id: int) -> list[TechnicalStageTiming]:
        return (
            db.query(TechnicalStageTiming)
            .options(joinedload(TechnicalStageTiming.user))
            .filter(TechnicalStageTiming.repair_order_id == repair_order_id)
            .order_by(TechnicalStageTiming.started_at.asc())
            .all()
        )
