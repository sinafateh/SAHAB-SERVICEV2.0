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

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ایجاد پوشه آپلود
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "photos"), exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "attachments"), exist_ok=True)

# ایجاد جدول‌ها
Base.metadata.create_all(bind=engine)

# ============================================
# ایجاد اپلیکیشن
# ============================================
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="سیستم مدیریت تعمیرات تجهیزات اعلام و اطفا حریق",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# تنظیم CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Mount static files
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
    file_path = os.path.join("frontend", "templates", filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>خطا</title></head>
        <body style="font-family:Tahoma;text-align:center;padding:50px;">
            <h1 style="color:red;">فایل {filename} پیدا نشد!</h1>
        </body>
        </html>
        """

# ============================================
# صفحات UI (با محافظت از احراز هویت)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def home():
    return read_html_file("index.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return read_html_file("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    return read_html_file("dashboard.html")

@app.get("/orders", response_class=HTMLResponse)
async def orders_page():
    return read_html_file("orders.html")

@app.get("/new-order", response_class=HTMLResponse)
async def new_order_page():
    return read_html_file("new_order.html")

@app.get("/order/{order_id}", response_class=HTMLResponse)
async def order_detail_page(order_id: int):
    html = read_html_file("order_detail.html")
    html = html.replace("{{ORDER_ID}}", str(order_id))
    return html

@app.get("/users", response_class=HTMLResponse)
async def users_page():
    return read_html_file("users.html")

@app.get("/health")
async def health_check():
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        return {"status": "سالم", "database": "متصل"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "مشکل", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )