from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # ============================================
    # دیتابیس - PostgreSQL
    # ============================================
    database_url: str = "postgresql://postgres:admin1234@localhost:5432/SAHAB_Service"
    
    # ============================================
    # برنامه
    # ============================================
    app_name: str = "سیستم مدیریت تعمیرات سها"
    debug: bool = True
    secret_key: str = "my-secret-key-12345-change-this-in-production"
    
    # ============================================
    # JWT
    # ============================================
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production-987654321"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 روز
    
    # ============================================
    # آپلود فایل
    # ============================================
    upload_dir: str = "./uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10 مگابایت
    
    # ============================================
    # CORS
    # ============================================
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """تبدیل رشته CSV به لیست"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# ایجاد نمونه از تنظیمات
settings = Settings()