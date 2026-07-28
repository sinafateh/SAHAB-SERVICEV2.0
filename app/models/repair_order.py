from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
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

class RepairOrder(Base):
    __tablename__ = "repair_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String(20), unique=True, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.REGISTERED)
    
    reception_date = Column(DateTime, server_default=func.now())
    technical_review_date = Column(DateTime, nullable=True)
    diagnosis_date = Column(DateTime, nullable=True)
    repair_start_date = Column(DateTime, nullable=True)
    repair_complete_date = Column(DateTime, nullable=True)
    final_delivery_date = Column(DateTime, nullable=True)
    
    customer_complaint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    device = relationship("Device", backref="repair_orders")
    customer = relationship("Customer", backref="repair_orders")