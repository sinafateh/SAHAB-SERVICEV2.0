from sqlalchemy import create_engine, text  # ✅ اضافه کردن text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# ============================================
# تنظیمات اتصال به دیتابیس PostgreSQL
# ============================================
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================
# تابع دریافت سشن دیتابیس
# ============================================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"خطا در سشن دیتابیس: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# ============================================
# تابع تست اتصال (اصلاح شده)
# ============================================
def test_connection() -> bool:
    """تست اتصال به دیتابیس"""
    try:
        db = SessionLocal()
        # ✅ استفاده از text() برای SQL خام
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ اتصال به دیتابیس برقرار شد")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در اتصال به دیتابیس: {e}")
        return False

# تست اتصال در زمان بارگذاری
if not test_connection():
    logger.warning("⚠️ اتصال به دیتابیس برقرار نشد! لطفاً تنظیمات را بررسی کنید.")