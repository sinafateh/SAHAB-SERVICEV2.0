from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Attachment(Base):
    __tablename__ = "attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # photo, document, pdf, video
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # ✅ اضافه شدن فیلدهای جدید
    is_physical_damage = Column(Boolean, default=False)  # آیا عکس برای وضعیت ظاهری است
    
    uploaded_by = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    repair_order_id = Column(Integer, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False)
    
    repair_order = relationship("RepairOrder", backref="attachments")