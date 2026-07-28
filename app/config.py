from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # دیتابیس
    database_url: str = "sqlite:///./repair_system.db"
    
    # برنامه
    app_name: str = "سیستم مدیریت تعمیرات"
    debug: bool = True
    secret_key: str = "my-secret-key-12345"
    
    # JWT
    jwt_secret_key: str = "your-super-secret-jwt-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    
    # آپلود
    upload_dir: str = "./uploads"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()