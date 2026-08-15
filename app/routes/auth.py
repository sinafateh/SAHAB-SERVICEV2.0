from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_active_user, get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
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
    if user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نقش نامعتبر. نقش‌های مجاز: {', '.join(VALID_ROLES)}"
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
        if user_data.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"نقش نامعتبر. نقش‌های مجاز: {', '.join(VALID_ROLES)}"
            )
        user.role = user_data.role
    if user_data.department is not None:
        user.department = user_data.department
    expected_department = ROLE_DEPARTMENTS.get(user.role)
    if expected_department:
        user.department = expected_department
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
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
    
    db.delete(user)
    db.commit()
    
    logger.info(f"✅ کاربر {user.username} حذف شد توسط {current_user.username}")
    
    return {"message": "کاربر با موفقیت حذف شد"}

# ============================================
# 8. خروج از سیستم
# ============================================
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
