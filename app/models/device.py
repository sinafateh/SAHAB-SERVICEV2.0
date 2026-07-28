from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
import enum
from app.models.base import Base

class PhysicalCondition(str, enum.Enum):
    HEALTHY = "سالم"
    BROKEN = "شکستگی"
    BURN = "آثار سوختگی"
    TAMPERED = "دستکاری شده"
    CORRODED = "خوردگی"
    WATER_DAMAGE = "آب خوردگی"

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    part_number = Column(String(100), nullable=False, index=True)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    firmware_version = Column(String(50))
    physical_condition = Column(Enum(PhysicalCondition))
    physical_condition_notes = Column(Text)
    photo_paths = Column(JSON, default=list)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer = relationship("Customer", backref="devices")
    
    # ✅ اضافه کردن ایندکس‌های ترکیبی برای بهبود سرعت جستجو
    __table_args__ = (
        Index('ix_devices_part_number', 'part_number'),
        Index('ix_devices_serial_number', 'serial_number', unique=True),
        Index('ix_devices_brand_model', 'brand', 'model'),
        Index('ix_devices_brand', 'brand'),
        Index('ix_devices_model', 'model'),
    )