from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class OrderStatus(str, enum.Enum):
    REGISTERED = "ثبت شده"
    WAITING_TECHNICAL = "در انتظار بررسی فنی"
    DIAGNOSING = "در حال عیب‌یابی"
    WAITING_APPROVAL = "در انتظار تایید مشتری"
    REPAIRING = "در حال تعمیر"
    TESTING = "در حال تست"
    FINAL_CONTROL = "کنترل نهایی"
    READY_DELIVERY = "آماده تحویل"
    DELIVERED = "تحویل شده"
    CLOSED_NO_REPAIR = "مختومه بدون تعمیر"

class PhysicalDamage(str, enum.Enum):
    BROKEN = "شکستگی"
    BURN = "سوختگی"
    WATER_DAMAGE = "آب خوردگی"
    CORRODED = "زنگ زدگی"
    IMPACT = "ضربه"
    TAMPERED = "دستکاری"
    MISSING_SCREW = "پیچ مفقود"
    NO_DAMAGE = "بدون ایراد ظاهری"

class Accessory(str, enum.Enum):
    BATTERY = "باتری"
    CABLE = "کابل"
    FUSE = "فیوز"
    MANUAL = "دفترچه"
    BOX = "جعبه"
    CONNECTOR = "کانکتور"
    LOOP_CARD = "کارت لوپ"
    EXTRA_BOARD = "برد اضافه"
    OTHER = "سایر"

class DeliveryMethod(str, enum.Enum):
    IN_PERSON = "حضوری"
    COURIER = "پیک"
    TIPAX = "تیپاکس"
    BARBARI = "باربری"
    POST = "پست"
    OTHER = "سایر"

class RepairOrder(Base):
    __tablename__ = "repair_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String(20), unique=True, nullable=False)
    qr_code = Column(Text, nullable=True)  # ذخیره مسیر QR Code
    
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.REGISTERED)
    
    # ============================================
    # اطلاعات پذیرش (Auto)
    # ============================================
    reception_date = Column(DateTime, server_default=func.now())
    operator_name = Column(String(100), nullable=True)  # اپراتور پذیرش
    
    # ============================================
    # اطلاعات مشتری (Customer)
    # ============================================
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # ============================================
    # محل نصب (Site)
    # ============================================
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    
    # ============================================
    # مسئول ارسال پنل
    # ============================================
    sender_name = Column(String(100), nullable=True)
    sender_position = Column(String(100), nullable=True)
    sender_phone = Column(String(20), nullable=True)
    sender_landline = Column(String(20), nullable=True)
    
    delivery_method = Column(Enum(DeliveryMethod), nullable=True)
    courier_company = Column(String(100), nullable=True)  # اگر پیک
    courier_tracking = Column(String(100), nullable=True)  # شماره مرسوله
    
    # ============================================
    # اطلاعات پنل (Panel)
    # ============================================
    panel_id = Column(Integer, ForeignKey("panels.id"), nullable=True)
    
    # ============================================
    # وضعیت ظاهری
    # ============================================
    physical_damages = Column(JSON, default=list)  # لیست PhysicalDamage
    physical_description = Column(Text, nullable=True)
    
    # ============================================
    # متعلقات
    # ============================================
    accessories = Column(JSON, default=list)  # لیست Accessory
    accessories_description = Column(Text, nullable=True)
    
    # ============================================
    # شرح مشتری
    # ============================================
    customer_complaint = Column(Text, nullable=True)
    
    # ============================================
    # یادداشت‌ها
    # ============================================
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    
    # ============================================
    # تاریخ‌های کلیدی
    # ============================================
    technical_review_date = Column(DateTime, nullable=True)
    diagnosis_date = Column(DateTime, nullable=True)
    repair_start_date = Column(DateTime, nullable=True)
    repair_complete_date = Column(DateTime, nullable=True)
    final_delivery_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # ============================================
    # روابط
    # ============================================
    customer = relationship("Customer", backref="repair_orders")
    panel = relationship("Panel", backref="repair_orders")