from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
import shutil
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from app.database import get_db
from app.models import (
    Attachment,
    Board,
    CaseTimelineEvent,
    Notification,
    RepairOrder,
    StatusHistory,
    TechnicalStageTiming,
    User,
    WorkflowTransition,
)
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_active_user, get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, PRIVILEGED_ROLES,
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# ============================================
# ایجاد Router
# ============================================
router = APIRouter(prefix="/auth", tags=["احراز هویت"])

# ============================================
# مدل‌های Pydantic
# ============================================

class TokenResponse(BaseModel):
    """پاسخ توکن"""
    access_token: str
    token_type: str = "bearer"
    id: int
    username: str
    full_name: str
    role: str
    department: Optional[str] = None
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # تبدیل به ثانیه

class UserRegister(BaseModel):
    """ثبت نام کاربر جدید"""
    username: str = Field(..., min_length=3, max_length=50, description="نام کاربری")
    password: str = Field(..., min_length=6, max_length=100, description="رمز عبور")
    full_name: str = Field(..., min_length=2, max_length=100, description="نام کامل")
    email: Optional[EmailStr] = Field(None, description="ایمیل")
    phone: Optional[str] = Field(None, max_length=20, description="شماره تماس")
    role: str = Field("VIEWER", description="نقش کاربر")
    department: Optional[str] = Field(None, max_length=50)

class UserUpdate(BaseModel):
    """بروزرسانی اطلاعات کاربر"""
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    department: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)

class ChangePassword(BaseModel):
    """تغییر رمز عبور"""
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)

class UserResponse(BaseModel):
    """پاسخ اطلاعات کاربر"""
    id: int
    username: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    role: str
    department: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============================================
# لیست نقش‌های معتبر
# ============================================
VALID_ROLES = ["ADMIN", "RECEPTION", "CUSTOMER_RELATIONS", "TECHNICAL", "MANAGEMENT", "VIEWER"]
MANAGEABLE_ROLES = ["ADMIN", "MANAGEMENT", "TECHNICAL", "RECEPTION", "CUSTOMER_RELATIONS"]
ROLE_DEPARTMENTS = {
    "RECEPTION": "RECEPTION",
    "CUSTOMER_RELATIONS": "CUSTOMER_RELATIONS",
    "TECHNICAL": "TECHNICAL",
    "MANAGEMENT": "MANAGEMENT",
}

# ============================================
# 1. ورود به سیستم
# ============================================
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    ورود کاربر و دریافت توکن JWT
    """
    logger.info(f"تلاش برای ورود: {form_data.username}")
    
    # جستجوی کاربر
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        logger.warning(f"کاربر یافت نشد: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # بررسی رمز عبور
    if not verify_password(form_data.password, user.password_hash):
        logger.warning(f"رمز عبور اشتباه برای کاربر: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # بررسی فعال بودن کاربر
    if not user.is_active:
        logger.warning(f"کاربر غیرفعال: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری شما غیرفعال است"
        )
    
    # بروزرسانی زمان آخرین ورود
    user.last_login = datetime.now()
    db.commit()
    
    # ایجاد توکن
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    logger.info(f"✅ ورود موفق: {user.username}")
    
    return TokenResponse(
        access_token=access_token,
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# ============================================
# 2. ثبت نام کاربر جدید (فقط مدیران)
# ============================================
@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    ثبت نام کاربر جدید - فقط ادمین
    """
    logger.info(f"ثبت نام کاربر جدید توسط: {current_user.username}")
    
    # بررسی وجود نام کاربری
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این نام کاربری قبلاً ثبت شده است"
        )
    
    # بررسی وجود ایمیل
    if user_data.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این ایمیل قبلاً ثبت شده است"
            )
    
    # بررسی نقش معتبر
    if user_data.role not in MANAGEABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نقش نامعتبر. نقش‌های مجاز: {', '.join(MANAGEABLE_ROLES)}"
        )

    expected_department = ROLE_DEPARTMENTS.get(user_data.role)
    if expected_department and user_data.department and user_data.department != expected_department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="بخش انتخاب‌شده با نقش کاربر سازگار نیست",
        )
    if expected_department and not user_data.department:
        user_data.department = expected_department
    
    # هش کردن رمز عبور
    hashed_password = get_password_hash(user_data.password)
    
    # ایجاد کاربر جدید
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        department=user_data.department,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"✅ کاربر جدید ثبت شد: {new_user.username}")
    
    return new_user

# ============================================
# 3. دریافت اطلاعات کاربر جاری
# ============================================
@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    دریافت اطلاعات کاربر جاری
    """
    return current_user

# ============================================
# 4. تغییر رمز عبور
# ============================================
@router.post("/change-password")
def change_password(
    data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    تغییر رمز عبور کاربر جاری
    """
    # بررسی رمز فعلی
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رمز عبور فعلی اشتباه است"
        )
    
    # بروزرسانی رمز جدید
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    
    logger.info(f"✅ رمز عبور کاربر {current_user.username} تغییر کرد")
    
    return {"message": "رمز عبور با موفقیت تغییر کرد"}

# ============================================
# 5. لیست کاربران (فقط مدیران)
# ============================================
@router.get("/users", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    دریافت لیست همه کاربران - فقط ادمین
    """
    users = db.query(User).order_by(User.id).all()
    return users

# ============================================
# 6. بروزرسانی کاربر (فقط مدیران)
# ============================================
@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    بروزرسانی اطلاعات کاربر - فقط ادمین
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر یافت نشد"
        )
    
    # جلوگیری از غیرفعال کردن خود
    if user.id == current_user.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نمی‌توانید خودتان را غیرفعال کنید"
        )
    
    # بروزرسانی فیلدها
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.role is not None:
        if user_data.role not in MANAGEABLE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نقش نامعتبر. نقش‌های مجاز: {', '.join(MANAGEABLE_ROLES)}"
            )
        user.role = user_data.role
    if user_data.department is not None:
        user.department = user_data.department
    expected_department = ROLE_DEPARTMENTS.get(user.role)
    if expected_department:
        user.department = expected_department
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ کاربر {user.username} بروزرسانی شد توسط {current_user.username}")
    
    return user

# ============================================
# 7. حذف کاربر (فقط مدیران)
# ============================================
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    حذف کاربر - فقط ادمین
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر یافت نشد"
        )
    
    # جلوگیری از حذف خود
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نمی‌توانید خودتان را حذف کنید"
        )

    if user.role in PRIVILEGED_ROLES:
        privileged_count = (
            db.query(User)
            .filter(User.role.in_(PRIVILEGED_ROLES), User.is_active.is_(True))
            .count()
        )
        if privileged_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حداقل یک مدیر فعال باید در سامانه باقی بماند.",
            )

    has_history = any(
        (
            db.query(WorkflowTransition)
            .filter(
                or_(
                    WorkflowTransition.from_user_id == user.id,
                    WorkflowTransition.to_user_id == user.id,
                )
            )
            .count(),
            db.query(StatusHistory)
            .filter(StatusHistory.changed_by == user.id)
            .count(),
        )
    )
    if has_history:
        user.is_active = False
        db.commit()
        return {
            "message": "این کاربر سابقه عملیاتی دارد و برای حفظ تاریخچه غیرفعال شد.",
            "deactivated": True,
        }
    
    db.delete(user)
    db.commit()
    
    logger.info(f"✅ کاربر {user.username} حذف شد توسط {current_user.username}")
    
    return {"message": "کاربر با موفقیت حذف شد"}

# ============================================
# 8. خروج از سیستم
# ============================================
class PurgeRepairOrdersRequest(BaseModel):
    confirmation: str = Field(..., min_length=10, max_length=50)


PURGE_CONFIRMATION = "DELETE_ALL_REPAIR_ORDERS"


@router.post("/repair-orders/purge")
def purge_all_repair_orders(
    payload: PurgeRepairOrdersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """حذف کامل پرونده‌ها و داده‌های وابسته؛ فقط برای مدیرکل/مدیریت."""
    if payload.confirmation != PURGE_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"برای تأیید باید عبارت {PURGE_CONFIRMATION} ارسال شود.",
        )

    order_ids = [item[0] for item in db.query(RepairOrder.id).all()]
    if not order_ids:
        return {"deleted_count": 0, "message": "پرونده‌ای برای حذف وجود ندارد."}

    upload_root = Path(settings.upload_dir).resolve()
    attachment_paths = [
        item[0]
        for item in db.query(Attachment.file_path)
        .filter(Attachment.repair_order_id.in_(order_ids))
        .all()
    ]
    for file_path in attachment_paths:
        if not file_path:
            continue
        relative_path = file_path.removeprefix("/uploads/").lstrip("/\\")
        candidate = (upload_root / relative_path).resolve()
        if upload_root in candidate.parents and candidate.is_file():
            try:
                candidate.unlink()
            except OSError:
                logger.warning("Could not remove attachment file: %s", candidate)

    child_models = [
        Attachment,
        Board,
        StatusHistory,
        WorkflowTransition,
        TechnicalStageTiming,
        CaseTimelineEvent,
    ]
    for model in child_models:
        db.query(model).filter(model.repair_order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
    db.query(Notification).filter(Notification.repair_order_id.in_(order_ids)).delete(
        synchronize_session=False
    )
    deleted_count = db.query(RepairOrder).filter(RepairOrder.id.in_(order_ids)).delete(
        synchronize_session=False
    )
    db.commit()

    for order_id in order_ids:
        for folder in ("photos", "attachments"):
            order_folder = (upload_root / folder / str(order_id)).resolve()
            if upload_root in order_folder.parents and order_folder.is_dir():
                shutil.rmtree(order_folder, ignore_errors=True)

    logger.warning(
        "All repair orders were purged by privileged user %s: %s records",
        current_user.username,
        deleted_count,
    )
    return {
        "deleted_count": deleted_count,
        "message": "همه پرونده‌ها و داده‌های وابسته با موفقیت حذف شدند.",
    }


@router.post("/logout")
def logout():
    """
    خروج از سیستم (سمت کلاینت توکن را حذف می‌کند)
    """
    return {"message": "با موفقیت خارج شدید"}

# ============================================
# 9. بررسی اعتبار توکن
# ============================================
@router.get("/verify")
def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    بررسی اعتبار توکن جاری
    """
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role
        }
    }
