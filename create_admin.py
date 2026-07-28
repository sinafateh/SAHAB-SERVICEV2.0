#!/usr/bin/env python3
"""
اسکریپت ایجاد کاربر ادمین برای سیستم مدیریت تعمیرات سها
با قابلیت اتصال به PostgreSQL و بروزرسانی رمز عبور
"""

import sys
import os
import argparse
from getpass import getpass

# اضافه کردن مسیر پروژه به PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, test_connection
from app.models.user import User
from app.auth import get_password_hash
from app.config import settings
import logging

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# کلاس مدیریت ادمین
# ============================================

class AdminManager:
    """مدیریت کاربر ادمین"""
    
    def __init__(self, db=None):
        self.db = db or SessionLocal()
    
    def create_or_update_admin(self, username: str = "admin", password: str = None) -> bool:
        """
        ایجاد یا بروزرسانی کاربر ادمین
        
        Args:
            username: نام کاربری (پیش‌فرض: admin)
            password: رمز عبور (اگر None باشد، از کاربر گرفته می‌شود)
        
        Returns:
            bool: موفقیت عملیات
        """
        try:
            # اگر رمز عبور داده نشده، از کاربر بگیر
            if not password:
                password = self._get_password()
                if not password:
                    logger.error("❌ رمز عبور وارد نشد")
                    return False
            
            # بررسی وجود کاربر
            admin = self.db.query(User).filter(User.username == username).first()
            
            if admin:
                return self._update_existing_admin(admin, password, username)
            else:
                return self._create_new_admin(username, password)
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ خطا در عملیات: {e}")
            return False
        finally:
            self.db.close()
    
    def _get_password(self) -> str:
        """دریافت رمز عبور از کاربر"""
        print("\n🔐 لطفاً رمز عبور را وارد کنید (حداقل ۶ کاراکتر):")
        while True:
            password = getpass("رمز عبور: ")
            if len(password) < 6:
                logger.warning("⚠️ رمز عبور باید حداقل ۶ کاراکتر باشد")
                continue
            confirm = getpass("تکرار رمز عبور: ")
            if password != confirm:
                logger.warning("⚠️ رمز عبور با تکرار آن مطابقت ندارد")
                continue
            return password
    
    def _create_new_admin(self, username: str, password: str) -> bool:
        """ایجاد کاربر ادمین جدید"""
        try:
            hashed_password = get_password_hash(password)
            
            admin = User(
                username=username,
                password_hash=hashed_password,
                full_name="مدیر سیستم",
                role="ADMIN",
                is_active=True
            )
            
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(admin)
            
            logger.info(f"✅ کاربر ادمین با نام کاربری '{username}' ایجاد شد")
            self._show_admin_info(admin)
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ خطا در ایجاد کاربر: {e}")
            return False
    
    def _update_existing_admin(self, admin: User, password: str, username: str) -> bool:
        """بروزرسانی کاربر ادمین موجود"""
        try:
            hashed_password = get_password_hash(password)
            
            # بروزرسانی اطلاعات
            admin.password_hash = hashed_password
            admin.is_active = True
            admin.role = "ADMIN"
            admin.full_name = "مدیر سیستم"
            
            self.db.commit()
            self.db.refresh(admin)
            
            logger.info(f"✅ کاربر ادمین با نام کاربری '{username}' بروزرسانی شد")
            self._show_admin_info(admin)
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ خطا در بروزرسانی کاربر: {e}")
            return False
    
    def _show_admin_info(self, admin: User):
        """نمایش اطلاعات کاربر ادمین"""
        print("\n" + "=" * 50)
        print("   📋 اطلاعات کاربر ادمین")
        print("=" * 50)
        print(f"   شناسه:     {admin.id}")
        print(f"   نام کاربری: {admin.username}")
        print(f"   نام کامل:   {admin.full_name}")
        print(f"   نقش:       {admin.role}")
        print(f"   وضعیت:     {'فعال' if admin.is_active else 'غیرفعال'}")
        print("=" * 50)
    
    def list_all_users(self):
        """نمایش لیست همه کاربران"""
        try:
            users = self.db.query(User).order_by(User.id).all()
            
            if not users:
                print("\n📭 هیچ کاربری در سیستم وجود ندارد")
                return
            
            print("\n" + "=" * 80)
            print("   📋 لیست کاربران سیستم")
            print("=" * 80)
            print(f"   {'ID':<5} {'نام کاربری':<15} {'نام کامل':<20} {'نقش':<15} {'وضعیت':<10}")
            print("-" * 80)
            
            for user in users:
                status = '✅ فعال' if user.is_active else '❌ غیرفعال'
                print(f"   {user.id:<5} {user.username:<15} {user.full_name:<20} {user.role:<15} {status:<10}")
            
            print("=" * 80)
            print(f"   مجموع کاربران: {len(users)}")
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیست کاربران: {e}")

# ============================================
# توابع کمکی برای خط فرمان
# ============================================

def check_database():
    """بررسی اتصال به دیتابیس"""
    print(f"\n📊 بررسی اتصال به دیتابیس: {settings.database_url}")
    
    if test_connection():
        print("✅ اتصال به دیتابیس برقرار است")
        return True
    else:
        print("❌ اتصال به دیتابیس برقرار نیست")
        print(f"   لطفاً تنظیمات دیتابیس را در فایل .env بررسی کنید")
        print(f"   DATABASE_URL={settings.database_url}")
        return False

def show_help():
    """نمایش راهنما"""
    print("""
    🔧 راهنمای استفاده از اسکریپت create_admin.py
    
    استفاده:
        python create_admin.py [options]
    
    گزینه‌ها:
        -h, --help          نمایش این راهنما
        -u, --username      نام کاربری (پیش‌فرض: admin)
        -p, --password      رمز عبور (اگر وارد نشود، از کاربر گرفته می‌شود)
        -l, --list          نمایش لیست همه کاربران
        -c, --check         فقط بررسی اتصال به دیتابیس
    
    مثال‌ها:
        python create_admin.py                     # ایجاد ادمین با نام admin
        python create_admin.py -u manager          # ایجاد ادمین با نام manager
        python create_admin.py -p admin123         # ایجاد ادمین با رمز admin123
        python create_admin.py -l                  # نمایش لیست کاربران
        python create_admin.py -c                  # بررسی اتصال به دیتابیس
    """)

# ============================================
# تابع اصلی
# ============================================

def main():
    """تابع اصلی برنامه"""
    parser = argparse.ArgumentParser(
        description="ایجاد کاربر ادمین برای سیستم مدیریت تعمیرات سها",
        add_help=False
    )
    parser.add_argument('-h', '--help', action='store_true', help='نمایش راهنما')
    parser.add_argument('-u', '--username', default='admin', help='نام کاربری (پیش‌فرض: admin)')
    parser.add_argument('-p', '--password', help='رمز عبور (اگر وارد نشود، از کاربر گرفته می‌شود)')
    parser.add_argument('-l', '--list', action='store_true', help='نمایش لیست کاربران')
    parser.add_argument('-c', '--check', action='store_true', help='بررسی اتصال به دیتابیس')
    
    args = parser.parse_args()
    
    # نمایش راهنما
    if args.help:
        show_help()
        return
    
    # بررسی اتصال به دیتابیس
    if args.check:
        check_database()
        return
    
    # نمایش لیست کاربران
    if args.list:
        if not check_database():
            return
        manager = AdminManager()
        manager.list_all_users()
        return
    
    # ایجاد یا بروزرسانی ادمین
    print("=" * 60)
    print("   🚀 ایجاد کاربر ادمین سیستم مدیریت تعمیرات سها")
    print("=" * 60)
    
    # بررسی اتصال به دیتابیس
    if not check_database():
        sys.exit(1)
    
    # ایجاد مدیریت
    manager = AdminManager()
    
    # اجرا
    success = manager.create_or_update_admin(
        username=args.username,
        password=args.password
    )
    
    if success:
        print("\n✅ عملیات با موفقیت انجام شد")
        print("\n⚠️  لطفاً رمز عبور را در محیط تولید تغییر دهید!")
        print("🔑 می‌توانید با دستور زیر رمز را تغییر دهید:")
        print(f"   python create_admin.py -u {args.username}")
        sys.exit(0)
    else:
        print("\n❌ عملیات با خطا مواجه شد")
        sys.exit(1)

# ============================================
# اجرای مستقیم
# ============================================

if __name__ == "__main__":
    main()