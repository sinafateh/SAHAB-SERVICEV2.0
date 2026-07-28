from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.repair_order import OrderStatus

class StatusHistory(Base):
    __tablename__ = "status_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    old_status = Column(Enum(OrderStatus), nullable=True)
    new_status = Column(Enum(OrderStatus), nullable=False)
    reason = Column(Text, nullable=True)
    operator_name = Column(String(100), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, server_default=func.now())
    repair_order_id = Column(Integer, ForeignKey("repair_orders.id"), nullable=False)
    
    repair_order = relationship("RepairOrder", backref="status_histories")