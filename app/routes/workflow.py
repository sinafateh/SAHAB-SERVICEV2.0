from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user
from app.database import get_db
from app.models.repair_order import OrderStatus, RepairOrder
from app.models.attachment import Attachment
from app.models.case_timeline_event import CaseTimelineEvent
from app.models.technical_stage_timing import TechnicalStageTiming
from app.models.status_history import StatusHistory
from app.models.user import User
from app.models.workflow_transition import WorkflowTransition
from app.schemas.workflow import (
    WorkflowActionRequest,
    WorkflowRejectRequest,
    WorkflowRecipientChangeRequest,
    WorkflowStageResponse,
    WorkflowTaskResponse,
    WorkflowTransferRequest,
    WorkflowTransitionResponse,
    TechnicalTimingRequest,
)
from app.services.workflow_service import DEPARTMENTS, STAGES, WorkflowService


router = APIRouter(prefix="/api/workflow", tags=["Workflow"])


def transition_response(item) -> WorkflowTransitionResponse:
    return WorkflowTransitionResponse(
        transition_id=item.id,
        repair_order_id=item.repair_order_id,
        from_user_id=item.from_user_id,
        from_user_name=item.from_user.full_name if item.from_user else None,
        to_user_id=item.to_user_id,
        to_user_name=item.to_user.full_name if item.to_user else None,
        from_department=item.from_department,
        to_department=item.to_department,
        action=item.action,
        stage=item.stage,
        note=item.note,
        status=item.status,
        rejection_reason=item.rejection_reason,
        is_received=item.is_received,
        received_by=item.received_by,
        received_at=item.received_at,
        rejected_at=item.rejected_at,
        created_at=item.created_at,
    )


@router.get("/stages", response_model=List[WorkflowStageResponse])
def get_stages(current_user: User = Depends(get_current_active_user)):
    return [
        WorkflowStageResponse(code=code, label=config["label"], department=config["department"])
        for code, config in STAGES.items()
    ]


@router.get("/departments")
def get_departments(current_user: User = Depends(get_current_active_user)):
    return [{"code": code, "label": label} for code, label in DEPARTMENTS.items()]


@router.get("/departments/{department}/users")
def get_department_users(
    department: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=404, detail="بخش پیدا نشد")
    users = (
        db.query(User)
        .filter(User.is_active.is_(True), User.department == department)
        .order_by(User.full_name.asc())
        .all()
    )
    return [
        {
            "id": item.id,
            "username": item.username,
            "full_name": item.full_name,
            "role": item.role,
            "department": item.department,
        }
        for item in users
    ]


@router.get("/orders/{repair_order_id}/state")
def get_order_workflow_state(
    repair_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    pending = WorkflowService.pending_transition(db, repair_order_id)
    return {
        "repair_order_id": order.id,
        "tracking_code": order.tracking_code,
        "current_stage": order.current_stage,
        "current_user_id": order.current_user_id,
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "quoted_price": order.quoted_price,
        "customer_approval": order.customer_approval,
        "pending_transition": transition_response(pending).model_dump() if pending else None,
    }


@router.post(
    "/orders/{repair_order_id}/transfer",
    response_model=WorkflowTransitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def transfer_order(
    repair_order_id: int,
    payload: WorkflowTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    transition = WorkflowService.transfer_order(
        db=db,
        order=order,
        current_user=current_user,
        to_user_id=payload.to_user_id,
        to_department=payload.to_department,
        stage=payload.stage,
        note=payload.note,
    )
    return transition_response(transition)


@router.get("/my-tasks", response_model=List[WorkflowTaskResponse])
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return [transition_response(item) for item in WorkflowService.get_my_tasks(db, current_user.id)]


@router.post("/transitions/{transition_id}/receive", response_model=WorkflowTransitionResponse)
def receive_transition(
    transition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return transition_response(WorkflowService.receive_transition(db, transition_id, current_user))


@router.post("/transitions/{transition_id}/reject", response_model=WorkflowTransitionResponse)
def reject_transition(
    transition_id: int,
    payload: WorkflowRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return transition_response(
        WorkflowService.reject_transition(db, transition_id, current_user, payload.reason)
    )


@router.patch("/transitions/{transition_id}/recipient", response_model=WorkflowTransitionResponse)
def change_recipient(
    transition_id: int,
    payload: WorkflowRecipientChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return transition_response(
        WorkflowService.change_recipient(
            db,
            transition_id,
            current_user,
            payload.to_user_id,
            payload.to_department,
        )
    )


@router.get("/orders/{repair_order_id}/history", response_model=List[WorkflowTransitionResponse])
def get_order_history(
    repair_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    WorkflowService.get_order(db, repair_order_id)
    transitions = (
        db.query(WorkflowTransition)
        .filter(WorkflowTransition.repair_order_id == repair_order_id)
        .order_by(WorkflowTransition.created_at.asc())
        .all()
    )
    return [transition_response(item) for item in transitions]


def timing_response(item: TechnicalStageTiming) -> dict:
    return {
        "id": item.id,
        "repair_order_id": item.repair_order_id,
        "stage": item.stage,
        "status": item.status,
        "user_id": item.user_id,
        "user_name": item.user.full_name if item.user else None,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
        "duration_seconds": item.duration_seconds,
        "note": item.note,
    }


@router.post("/orders/{repair_order_id}/timing/start")
def start_technical_timing(
    repair_order_id: int,
    payload: TechnicalTimingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    return timing_response(
        WorkflowService.start_timing(db, order, current_user, payload.stage, payload.note)
    )


@router.post("/orders/{repair_order_id}/timing/complete")
def complete_technical_timing(
    repair_order_id: int,
    payload: TechnicalTimingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    return timing_response(
        WorkflowService.complete_timing(db, order, current_user, payload.stage, payload.note)
    )


@router.get("/orders/{repair_order_id}/timings")
def get_technical_timings(
    repair_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    WorkflowService.get_order(db, repair_order_id)
    return [timing_response(item) for item in WorkflowService.get_timings(db, repair_order_id)]


@router.get("/orders/{repair_order_id}/timeline")
def get_case_timeline(
    repair_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    events = (
        db.query(CaseTimelineEvent)
        .options(joinedload(CaseTimelineEvent.actor))
        .filter(CaseTimelineEvent.repair_order_id == repair_order_id)
        .all()
    )
    transitions = (
        db.query(WorkflowTransition)
        .options(joinedload(WorkflowTransition.from_user), joinedload(WorkflowTransition.to_user))
        .filter(WorkflowTransition.repair_order_id == repair_order_id)
        .all()
    )
    attachments = (
        db.query(Attachment)
        .filter(Attachment.repair_order_id == repair_order_id)
        .all()
    )
    status_history = (
        db.query(StatusHistory)
        .filter(StatusHistory.repair_order_id == repair_order_id)
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )
    result = [
        {
            "id": f"event-{item.id}",
            "event_type": item.event_type,
            "title": item.title,
            "description": item.description,
            "stage": item.stage,
            "actor_name": item.actor.full_name if item.actor else None,
            "created_at": item.created_at,
            "metadata": item.metadata_json,
        }
        for item in events
    ]
    existing_transition_ids = {
        (item.metadata_json or {}).get("transition_id")
        for item in events
        if item.event_type.startswith("TRANSFER") or item.event_type == "RECIPIENT_CHANGED"
    }
    for item in transitions:
        if item.id in existing_transition_ids:
            continue
        result.append(
            {
                "id": f"transition-{item.id}",
                "event_type": "TRANSFER",
                "title": "انتقال پرونده",
                "description": f"{item.from_user.full_name if item.from_user else '-'} ← {item.to_user.full_name if item.to_user else '-'}",
                "stage": item.stage,
                "actor_name": item.from_user.full_name if item.from_user else None,
                "created_at": item.created_at,
                "metadata": {"transition_id": item.id, "status": item.status},
            }
        )
    for item in attachments:
        if item.id in {
            (event.metadata_json or {}).get("attachment_id")
            for event in events
            if event.event_type == "ATTACHMENT_UPLOADED"
        }:
            continue
        result.append(
            {
                "id": f"attachment-{item.id}",
                "event_type": "ATTACHMENT",
                "title": "ثبت فایل مرحله‌ای",
                "description": item.file_name,
                "stage": getattr(item, "stage", None),
                "actor_name": getattr(item, "uploaded_by_name", None),
                "created_at": item.uploaded_at,
                "metadata": {
                    "attachment_id": item.id,
                    "file_path": item.file_path,
                    "uploaded_by_department": getattr(item, "uploaded_by_department", None),
                },
            }
        )
    for item in status_history:
        result.append(
            {
                "id": f"status-{item.id}",
                "event_type": "STATUS_CHANGED",
                "title": "تغییر وضعیت پرونده",
                "description": item.note or item.reason,
                "stage": None,
                "actor_name": item.operator_name,
                "created_at": item.changed_at,
                "metadata": {
                    "old_status": item.old_status.value if hasattr(item.old_status, "value") else item.old_status,
                    "new_status": item.new_status.value if hasattr(item.new_status, "value") else item.new_status,
                },
            }
        )
    if not result:
        result.append(
            {
                "id": "created",
                "event_type": "CASE_CREATED",
                "title": "ایجاد پرونده",
                "description": f"پرونده {order.tracking_code} ایجاد شد.",
                "stage": "RECEPTION_INTAKE",
                "actor_name": order.operator_name,
                "created_at": order.created_at or order.reception_date,
                "metadata": {},
            }
        )
    result.sort(
        key=lambda item: (
            item.get("created_at").timestamp()
            if item.get("created_at") is not None
            else 0
        )
    )
    return result


KANBAN_COLUMNS = [
    ("RECEPTION_INTAKE", "پذیرش", "RECEPTION"),
    ("TECHNICAL_DIAGNOSIS", "عیب یابی", "TECHNICAL"),
    ("MANAGEMENT_PRICING", "برآورد قیمت", "MANAGEMENT"),
    ("TECHNICAL_REPAIR", "تعمیر", "TECHNICAL"),
    ("TECHNICAL_FINAL_TEST", "تست", "TECHNICAL"),
    ("RECEPTION_DELIVERY", "آماده تحویل", "RECEPTION"),
]


@router.get("/kanban/board")
def get_kanban_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    columns = [
        {"stage": stage, "label": label, "department": department, "cards": []}
        for stage, label, department in KANBAN_COLUMNS
    ]
    by_stage = {item["stage"]: item for item in columns}
    stage_aliases = {"CUSTOMER_APPROVAL": "MANAGEMENT_PRICING"}
    orders = (
        db.query(RepairOrder)
        .options(joinedload(RepairOrder.current_user), joinedload(RepairOrder.customer))
        .filter(~RepairOrder.current_stage.in_(["COMPLETED", "CLOSED_NO_REPAIR"]))
        .order_by(RepairOrder.created_at.asc())
        .all()
    )
    pending_transitions = {
        item.repair_order_id: item
        for item in db.query(WorkflowTransition)
        .options(joinedload(WorkflowTransition.to_user))
        .filter(
            WorkflowTransition.repair_order_id.in_([item.id for item in orders]) if orders else False,
            WorkflowTransition.status == "PENDING",
        )
        .all()
    }
    for order in orders:
        column = by_stage.get(stage_aliases.get(order.current_stage, order.current_stage)) or by_stage["RECEPTION_INTAKE"]
        pending = pending_transitions.get(order.id)
        customer_name = None
        if order.customer:
            customer_name = " ".join(
                part for part in [
                    getattr(order.customer, "name", None),
                    getattr(order.customer, "last_name", None),
                ] if part
            ) or getattr(order.customer, "company", None)
        column["cards"].append(
            {
                "id": order.id,
                "tracking_code": order.tracking_code,
                "current_stage": order.current_stage,
                "status": order.status.value if hasattr(order.status, "value") else order.status,
                "display_status": "PENDING_TRANSFER" if pending else (order.status.value if hasattr(order.status, "value") else order.status),
                "is_pending_transfer": bool(pending),
                "pending_to_user_name": pending.to_user.full_name if pending and pending.to_user else None,
                "pending_stage": pending.stage if pending else None,
                "current_user_id": order.current_user_id,
                "current_user_name": order.current_user.full_name if order.current_user else None,
                "customer_name": customer_name,
                "device": f"{getattr(order.panel, 'brand', '') or ''} {getattr(order.panel, 'model', '') or ''}".strip(),
                "created_at": order.created_at,
            }
        )
    return {"columns": columns}


@router.get("/closed-orders")
def get_closed_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    orders = (
        db.query(RepairOrder)
        .options(
            joinedload(RepairOrder.customer),
            joinedload(RepairOrder.panel),
            joinedload(RepairOrder.current_user),
        )
        .filter(
            RepairOrder.status.in_(
                [OrderStatus.DELIVERED, OrderStatus.CLOSED_NO_REPAIR]
            )
        )
        .order_by(RepairOrder.delivered_at.desc(), RepairOrder.created_at.desc())
        .all()
    )
    return {
        "total": len(orders),
        "orders": [
            {
                "id": order.id,
                "tracking_code": order.tracking_code,
                "status": order.status.value if hasattr(order.status, "value") else order.status,
                "current_stage": order.current_stage,
                "customer_name": (
                    (
                        " ".join(
                            part
                            for part in [
                                getattr(order.customer, "name", None),
                                getattr(order.customer, "last_name", None),
                            ]
                            if part
                        )
                        or getattr(order.customer, "company", None)
                    )
                    if order.customer
                    else None
                ),
                "customer_phone": getattr(order.customer, "phone", None) if order.customer else None,
                "device": (
                    f"{getattr(order.panel, 'brand', '') or ''} "
                    f"{getattr(order.panel, 'model', '') or ''}"
                ).strip()
                if order.panel
                else None,
                "serial_number": getattr(order.panel, "serial_number", None) if order.panel else None,
                "delivered_at": order.delivered_at,
                "created_at": order.created_at,
                "current_user_name": (
                    order.current_user.full_name if order.current_user else None
                ),
            }
            for order in orders
        ],
    }


@router.post("/kanban/orders/{repair_order_id}/move", response_model=WorkflowTransitionResponse, status_code=201)
def move_kanban_card(
    repair_order_id: int,
    payload: WorkflowTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    return transition_response(
        WorkflowService.transfer_order(
            db, order, current_user, payload.to_user_id, payload.stage,
            payload.to_department, payload.note
        )
    )


@router.post("/orders/{repair_order_id}/action")
def apply_action(
    repair_order_id: int,
    payload: WorkflowActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = WorkflowService.get_order(db, repair_order_id)
    updated = WorkflowService.apply_action(
        db,
        order,
        current_user,
        payload.action,
        payload.notes,
        payload.quoted_price,
        payload.approved,
    )
    return {
        "repair_order_id": updated.id,
        "status": updated.status.value if hasattr(updated.status, "value") else updated.status,
        "current_stage": updated.current_stage,
        "quoted_price": updated.quoted_price,
        "customer_approval": updated.customer_approval,
    }
