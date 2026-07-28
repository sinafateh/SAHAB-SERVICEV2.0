from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from app.database import engine, get_db
from app.models import Base
from app.config import settings
from app.routes import reception, auth
from app.auth import get_current_user, get_current_active_user
import logging
import os
from sqlalchemy import text
# ============================================
# تنظیم لاگ
# ============================================
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# ایجاد پوشه‌های مورد نیاز
# ============================================
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "photos"), exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "attachments"), exist_ok=True)

# ============================================
# ایجاد جدول‌های دیتابیس
# ============================================
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ جدول‌های دیتابیس با موفقیت ایجاد شدند")
except Exception as e:
    logger.error(f"❌ خطا در ایجاد جدول‌های دیتابیس: {e}")

# ============================================
# ایجاد اپلیکیشن FastAPI
# ============================================
app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="سیستم مدیریت تعمیرات تجهیزات اعلام و اطفا حریق - شرکت سها",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# ============================================
# تنظیم CORS با محدودیت
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Mount فایل‌های استاتیک
# ============================================
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# ============================================
# ثبت روت‌های API
# ============================================
app.include_router(reception.router)
app.include_router(auth.router)

# ============================================
# تابع کمکی برای خواندن فایل‌های HTML
# ============================================
def read_html_file(filename: str) -> str:
    """خواندن فایل HTML از پوشه templates"""
    file_path = os.path.join("frontend", "templates", filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"فایل {filename} پیدا نشد")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>خطا</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
        </head>
        <body style="font-family:Tahoma;text-align:center;padding:50px;">
            <div class="container">
                <div class="alert alert-danger">
                    <h1>⚠️ فایل {filename} پیدا نشد!</h1>
                    <p>لطفاً با پشتیبانی تماس بگیرید.</p>
                    <a href="/" class="btn btn-primary">بازگشت به صفحه اصلی</a>
                </div>
            </div>
        </body>
        </html>
        """

# ============================================
# صفحات UI
# ============================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """صفحه اصلی"""
    return read_html_file("index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """صفحه ورود"""
    return read_html_file("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """داشبورد مدیریتی"""
    return read_html_file("dashboard.html")

@app.get("/orders", response_class=HTMLResponse)
async def orders_page():
    """لیست پرونده‌ها"""
    return read_html_file("orders.html")

@app.get("/new-order", response_class=HTMLResponse)
async def new_order_page():
    """ثبت پرونده جدید"""
    return read_html_file("new_order.html")

@app.get("/order/{order_id}", response_class=HTMLResponse)
async def order_detail_page(order_id: int):
    """جزئیات پرونده"""
    html = read_html_file("order_detail.html")
    # ✅ جایگزینی با شناسه واقعی
    html = html.replace("{{ORDER_ID}}", str(order_id))
    return html

@app.get("/users", response_class=HTMLResponse)
async def users_page():
    """مدیریت کاربران"""
    return read_html_file("users.html")

# ============================================
# API سلامت
# ============================================
@app.get("/health", operation_id="health_check_api")
async def health_check():
    """بررسی سلامت سیستم"""
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "app_name": settings.app_name,
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

# ============================================
# اجرای مستقیم
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
@app.get("/health")
async def health_check():
    """بررسی سلامت سیستم"""
    try:
        db = next(get_db())
        # ✅ استفاده از text()
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "app_name": settings.app_name,
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }