from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# ============================================
# تنظیمات رمزنگاری
# ============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ============================================
# دریافت تنظیمات از config
# ============================================
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes

# ============================================
# توابع رمزنگاری
# ============================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    بررسی رمز عبور با bcrypt
    در صورت خطا، False برمی‌گرداند
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"خطا در verify_password: {e}")
        return False

def get_password_hash(password: str) -> str:
    """
    هش کردن رمز عبور با bcrypt
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"خطا در get_password_hash: {e}")
        # Fallback به bcrypt مستقیم
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# ============================================
# توابع JWT
# ============================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    ایجاد توکن JWT
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """
    دیکد کردن توکن JWT
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"خطا در decode_access_token: {e}")
        raise

# ============================================
# توابع احراز هویت
# ============================================
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    دریافت کاربر جاری از توکن
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    دریافت کاربر فعال جاری
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    بررسی اینکه کاربر ادمین باشد
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can perform this action"
        )
    return current_user

async def get_current_technical_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    بررسی اینکه کاربر نقش فنی یا ادمین داشته باشد
    """
    if current_user.role not in ["ADMIN", "TECHNICAL"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only technical and admin users can perform this action"
        )
    return current_user

async def get_current_reception_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    بررسی اینکه کاربر نقش پذیرش یا ادمین داشته باشد
    """
    if current_user.role not in ["ADMIN", "RECEPTION", "CUSTOMER_RELATIONS"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only reception and admin users can perform this action"
        )
    return current_user