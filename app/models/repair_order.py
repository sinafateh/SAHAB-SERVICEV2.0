from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean, JSON, Numeric
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
    qr_code = Column(Text, nullable=True)
    
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.REGISTERED)
    current_stage = Column(String(50), nullable=False, default="RECEPTION_INTAKE", index=True)
    current_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # اطلاعات پذیرش (Auto)
    reception_date = Column(DateTime, server_default=func.now())
    operator_name = Column(String(100), nullable=True)
    
    # اطلاعات مشتری (Customer)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # محل نصب (Site)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    
    # اطلاعات پنل (Panel)
    panel_id = Column(Integer, ForeignKey("panels.id"), nullable=True)
    
    # مسئول ارسال پنل
    sender_name = Column(String(100), nullable=True)
    sender_position = Column(String(100), nullable=True)
    sender_phone = Column(String(20), nullable=True)
    sender_landline = Column(String(20), nullable=True)
    
    delivery_method = Column(Enum(DeliveryMethod), nullable=True)
    courier_company = Column(String(100), nullable=True)
    courier_tracking = Column(String(100), nullable=True)
    
    # وضعیت ظاهری
    physical_damages = Column(JSON, default=list)
    physical_description = Column(Text, nullable=True)
    
    # متعلقات
    accessories = Column(JSON, default=list)
    accessories_description = Column(Text, nullable=True)
    
    # شرح مشتری
    customer_complaint = Column(Text, nullable=True)
    diagnosis_notes = Column(Text, nullable=True)
    repair_notes = Column(Text, nullable=True)
    final_test_notes = Column(Text, nullable=True)
    quoted_price = Column(Numeric(14, 2), nullable=True)
    price_notes = Column(Text, nullable=True)
    customer_approval = Column(String(20), nullable=True)
    customer_approval_note = Column(Text, nullable=True)
    
    # یادداشت‌ها
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    
    # تاریخ‌های کلیدی
    technical_review_date = Column(DateTime, nullable=True)
    diagnosis_date = Column(DateTime, nullable=True)
    repair_start_date = Column(DateTime, nullable=True)
    repair_complete_date = Column(DateTime, nullable=True)
    final_delivery_date = Column(DateTime, nullable=True)
    price_decided_at = Column(DateTime, nullable=True)
    customer_response_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # ============================================
    # روابط (با نام‌های یکتا)
    # ============================================
    customer = relationship("Customer", backref="repair_orders")
    site = relationship("Site", backref="repair_orders")
    panel = relationship("Panel", backref="panel_repair_orders")  # ✅ نام یکتا
    current_user = relationship("User", foreign_keys=[current_user_id])
    transitions = relationship(
        "WorkflowTransition",
        back_populates="repair_order",
        cascade="all, delete-orphan",
    )
