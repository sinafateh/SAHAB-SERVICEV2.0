from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)  # ✅ برای اشخاص
    company = Column(String(100), nullable=True)    # ✅ برای سازمان‌ها
    phone = Column(String(20), nullable=False)
    phone_alternative = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)    # ✅ برای سازمان‌ها
    address = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('ix_customers_phone', 'phone'),
        Index('ix_customers_name', 'name'),
        Index('ix_customers_email', 'email'),
        Index('ix_customers_company', 'company'),
    )