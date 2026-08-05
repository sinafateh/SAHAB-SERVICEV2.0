from sqlalchemy import create_engine, text
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

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================
# تابع دریافت سشن دیتابیس برای Dependency
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
# تابع تست اتصال دیتابیس
# ============================================
def test_connection() -> bool:
    """
    تست اتصال به دیتابیس.
    این تابع فقط زمانی اجرا می‌شود که صراحتاً فراخوانی شود.
    """
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("✅ اتصال به دیتابیس برقرار شد")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در اتصال به دیتابیس: {e}")
        return False
    finally:
        db.close()
