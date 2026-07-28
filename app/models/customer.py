from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from app.models.base import Base

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    company = Column(String(100))
    phone = Column(String(20), nullable=False)
    phone_alternative = Column(String(20))
    email = Column(String(100))
    address = Column(String(500))
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # ✅ اضافه کردن ایندکس‌ها برای بهبود سرعت جستجو
    __table_args__ = (
        Index('ix_customers_phone', 'phone'),
        Index('ix_customers_name', 'name'),
        Index('ix_customers_email', 'email'),
        Index('ix_customers_company', 'company'),
    )