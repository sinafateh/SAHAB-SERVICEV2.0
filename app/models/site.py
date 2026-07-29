from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class SiteType(str, enum.Enum):
    RESIDENTIAL = "مسکونی"
    OFFICE = "اداری"
    COMMERCIAL = "تجاری"
    INDUSTRIAL = "صنعتی"
    HOSPITAL = "بیمارستان"
    HOTEL = "هتل"
    FACTORY = "کارخانه"
    EDUCATIONAL = "آموزشی"
    WAREHOUSE = "انبار"
    OTHER = "سایر"

class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(SiteType), nullable=False)
    address = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # اگر مسکونی
    building_name = Column(String(100), nullable=True)
    building_manager = Column(String(100), nullable=True)
    manager_phone = Column(String(20), nullable=True)
    lobby_phone = Column(String(20), nullable=True)
    
    # اگر سازمانی
    responsible_name = Column(String(100), nullable=True)
    responsible_position = Column(String(100), nullable=True)
    responsible_phone = Column(String(20), nullable=True)
    
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # ============================================
    # روابط (با نام‌های یکتا)
    # ============================================
    customer = relationship("Customer", backref="customer_sites")
    # ❌ رابطه repair_orders را حذف کنید (چون در RepairOrder تعریف می‌شود)