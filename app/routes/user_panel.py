from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user
from app.database import get_db
from app.models.notification import Notification
from app.models.repair_order import OrderStatus, RepairOrder
from app.models.user import User
from app.models.workflow_transition import WorkflowTransition
from app.schemas.user_panel import UserPanelResponse
from app.services.workflow_service import DEPARTMENTS


router = APIRouter(prefix="/api/panel", tags=["User Panel"])


@router.get("/me", response_model=UserPanelResponse)
def get_my_panel_info(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/notifications")
def get_my_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.post("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اعلان پیدا نشد")
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": notification.id, "is_read": notification.is_read, "read_at": notification.read_at}


@router.post("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .update(
            {
                Notification.is_read: True,
                Notification.read_at: datetime.now(timezone.utc),
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return {"updated_count": updated}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اعلان پیدا نشد")
    db.delete(notification)
    db.commit()
    return {"id": notification_id, "deleted": True}


@router.delete("/notifications")
def delete_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deleted = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted_count": deleted}


def _panel_case_response(order: RepairOrder, *, transfer: WorkflowTransition | None = None) -> dict:
    panel = order.panel
    customer = order.customer
    return {
        "repair_order_id": order.id,
        "tracking_code": order.tracking_code,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "current_stage": order.current_stage,
        "current_user_id": order.current_user_id,
        "customer_name": getattr(customer, "name", None),
        "panel_name": (
            " ".join(value for value in [getattr(panel, "brand", None), getattr(panel, "model", None)] if value)
            or None
        ),
        "serial_number": getattr(panel, "serial_number", None),
        "updated_at": order.updated_at or order.created_at,
        "created_at": order.created_at,
        "transfer_id": transfer.id if transfer else None,
        "transfer_status": transfer.status if transfer else None,
        "to_user_name": transfer.to_user.full_name if transfer and transfer.to_user else None,
        "to_department": transfer.to_department if transfer else None,
        "transferred_at": transfer.created_at if transfer else None,
    }


@router.get("/cases")
def get_my_panel_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    terminal_statuses = [
        OrderStatus.DELIVERED,
        OrderStatus.CLOSED_NO_REPAIR,
    ]

    pending_outgoing_order_ids = select(
        WorkflowTransition.repair_order_id
    ).where(
        WorkflowTransition.from_user_id == current_user.id,
        WorkflowTransition.status == "PENDING",
    )

    assigned_orders = (
        db.query(RepairOrder)
        .options(
            joinedload(RepairOrder.panel),
            joinedload(RepairOrder.customer),
        )
        .filter(
            RepairOrder.current_user_id == current_user.id,
            RepairOrder.status.notin_(terminal_statuses),
            ~RepairOrder.id.in_(pending_outgoing_order_ids),
        )
        .order_by(RepairOrder.updated_at.desc(), RepairOrder.created_at.desc())
        .all()
    )

    outgoing_transfers = (
        db.query(WorkflowTransition)
        .options(
            joinedload(WorkflowTransition.repair_order).joinedload(RepairOrder.panel),
            joinedload(WorkflowTransition.repair_order).joinedload(RepairOrder.customer),
            joinedload(WorkflowTransition.to_user),
        )
        .filter(
            WorkflowTransition.from_user_id == current_user.id,
            WorkflowTransition.status.in_(["PENDING", "RECEIVED"]),
        )
        .order_by(WorkflowTransition.created_at.desc())
        .all()
    )

    pending_tasks = (
        db.query(WorkflowTransition)
        .options(
            joinedload(WorkflowTransition.repair_order).joinedload(RepairOrder.panel),
            joinedload(WorkflowTransition.repair_order).joinedload(RepairOrder.customer),
            joinedload(WorkflowTransition.from_user),
        )
        .filter(
            WorkflowTransition.to_user_id == current_user.id,
            WorkflowTransition.status == "PENDING",
        )
        .order_by(WorkflowTransition.created_at.asc())
        .all()
    )

    return {
        "open": [_panel_case_response(order) for order in assigned_orders],
        "in_progress": [_panel_case_response(order) for order in assigned_orders],
        "transferred": [
            _panel_case_response(item.repair_order, transfer=item)
            for item in outgoing_transfers
        ],
        "pending_tasks": [
            {
                **_panel_case_response(item.repair_order),
                "transition_id": item.id,
                "from_user_name": item.from_user.full_name if item.from_user else None,
                "stage": item.stage,
                "note": item.note,
                "task_created_at": item.created_at,
            }
            for item in pending_tasks
        ],
    }


@router.get("/summary")
def get_my_panel_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )
    total = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    tasks = (
        db.query(WorkflowTransition)
        .filter(
            WorkflowTransition.to_user_id == current_user.id,
            WorkflowTransition.status == "PENDING",
        )
        .count()
    )
    active_cases = (
        db.query(RepairOrder)
        .filter(
            RepairOrder.current_user_id == current_user.id,
            RepairOrder.status.notin_(
                [OrderStatus.DELIVERED, OrderStatus.CLOSED_NO_REPAIR]
            ),
            ~RepairOrder.id.in_(
                select(WorkflowTransition.repair_order_id).where(
                    WorkflowTransition.from_user_id == current_user.id,
                    WorkflowTransition.status == "PENDING",
                )
            ),
        )
        .count()
    )
    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "role": current_user.role,
        "department": current_user.department,
        "unread_notifications_count": unread,
        "total_notifications_count": total,
        "active_tasks_count": tasks + active_cases,
        "active_cases_count": active_cases,
    }


@router.get("/departments")
def get_panel_departments(current_user: User = Depends(get_current_active_user)):
    return [{"code": code, "label": label} for code, label in DEPARTMENTS.items()]


@router.get("/users/by-department/{dept_name}", response_model=List[UserPanelResponse])
def get_users_by_department(
    dept_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if dept_name not in DEPARTMENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش پیدا نشد")
    return (
        db.query(User)
        .filter(User.department == dept_name, User.is_active.is_(True))
        .order_by(User.full_name.asc())
        .all()
    )
