from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["احراز هویت"])

# ============================================
# مدل‌های ورودی/خروجی
# ============================================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    full_name: str
    role: str

class UserRegister(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str = "VIEWER"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

VALID_ROLES = ["ADMIN", "RECEPTION", "CUSTOMER_RELATIONS", "TECHNICAL", "VIEWER"]

# ============================================
# 1. ورود به سیستم
# ============================================
@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user.last_login = datetime.now()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role
    }

# ============================================
# 2. ثبت نام کاربر جدید (فقط مدیران)
# ============================================
@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can register new users"
        )
    
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    if user_data.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    if user_data.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(VALID_ROLES)}"
        )
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# ============================================
# 3. دریافت اطلاعات کاربر فعلی
# ============================================
@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
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
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

# ============================================
# 5. لیست کاربران (فقط مدیران)
# ============================================
@router.get("/users", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view users list"
        )
    
    users = db.query(User).all()
    return users

# ============================================
# 6. بروزرسانی کاربر (فقط مدیران)
# ============================================
@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
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
                detail=f"Invalid role. Valid roles: {', '.join(VALID_ROLES)}"
            )
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    return user

# ============================================
# 7. حذف کاربر (فقط مدیران)
# ============================================
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

# ============================================
# 8. خروج از سیستم
# ============================================
@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}