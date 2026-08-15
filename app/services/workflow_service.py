from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.notification import Notification
from app.models.repair_order import OrderStatus, RepairOrder
from app.models.status_history import StatusHistory
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowService:
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

        if recipient.role != "ADMIN" and requested_department != config["department"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"گیرنده باید از بخش {DEPARTMENTS[config['department']]} باشد",
            )
        if recipient.role != "ADMIN" and department != config["department"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="بخش کاربر مقصد با مرحله‌ی انتخاب‌شده سازگار نیست",
            )
        return recipient, requested_department

    @staticmethod
    def ensure_sender_can_transfer(order: RepairOrder, current_user: User) -> None:
        if current_user.role == "ADMIN":
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
        if transition.from_user_id != current_user.id and current_user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="فقط فرستنده می‌تواند گیرنده را تغییر دهد")
        if transition.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="فقط انتقال باز قابل تغییر است")

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
        if order.current_user_id and order.current_user_id != current_user.id and current_user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="این پرونده در اختیار شما نیست")

        department = WorkflowService.effective_department(current_user)
        action = action.upper()
        now = utc_now()

        if action == "DIAGNOSIS":
            if department != "TECHNICAL":
                raise HTTPException(status_code=403, detail="ثبت عیب‌یابی فقط برای بخش فنی است")
            order.diagnosis_notes = notes
            order.diagnosis_date = now
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
        elif action == "FINAL_TEST":
            if department != "TECHNICAL":
                raise HTTPException(status_code=403, detail="ثبت تست نهایی فقط برای بخش فنی است")
            order.final_test_notes = notes
            if approved is False:
                raise HTTPException(status_code=400, detail="برای تست ناموفق باید پرونده به تعمیر بازگردانده شود")
            order.status = OrderStatus.FINAL_CONTROL
        elif action == "DELIVER":
            if department not in {"RECEPTION", "CUSTOMER_RELATIONS"}:
                raise HTTPException(status_code=403, detail="تحویل فقط برای پذیرش یا ارتباط با مشتریان است")
            order.delivered_at = now
            order.final_delivery_date = now
            order.status = OrderStatus.DELIVERED
            order.current_stage = "COMPLETED"
        else:
            raise HTTPException(status_code=400, detail="عملیات workflow معتبر نیست")

        db.commit()
        db.refresh(order)
        return order
