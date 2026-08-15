from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
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
    from app.models.workflow_transition import WorkflowTransition

    tasks = (
        db.query(WorkflowTransition)
        .filter(
            WorkflowTransition.to_user_id == current_user.id,
            WorkflowTransition.status == "PENDING",
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
        "active_tasks_count": tasks,
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
