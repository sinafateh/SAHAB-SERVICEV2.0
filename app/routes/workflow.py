from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.repair_order import RepairOrder
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
