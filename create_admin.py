from app.database import SessionLocal
from app.models.user import User
from app.auth import get_password_hash

def create_admin():
    db = SessionLocal()
    
    # حذف کاربر قبلی
    db.query(User).filter(User.username == 'admin').delete()
    db.commit()
    
    # ایجاد کاربر جدید
    hashed_password = get_password_hash("admin123")
    admin = User(
        username="admin",
        password_hash=hashed_password,
        full_name="مدیر سیستم",
        role="ADMIN",
        is_active=True
    )
    db.add(admin)
    db.commit()
    
    print("✅ کاربر admin با رمز admin123 ایجاد شد")
    db.close()

if __name__ == "__main__":
    create_admin()