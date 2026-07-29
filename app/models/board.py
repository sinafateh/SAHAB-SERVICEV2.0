from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
import enum

class BoardType(str, enum.Enum):
    MOTHER = "Mother Board"
    POWER = "Power Board"
    DISPLAY = "Display"
    CPU = "CPU"
    LOOP = "Loop Card"
    NETWORK = "Network"
    BATTERY_CHARGER = "Battery Charger"
    OTHER = "سایر"

class Board(Base):
    __tablename__ = "boards"
    
    id = Column(Integer, primary_key=True, index=True)
    board_type = Column(Enum(BoardType), nullable=False)
    part_number = Column(String(100), nullable=False)
    serial_number = Column(String(100), nullable=False)
    revision = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    
    repair_order_id = Column(Integer, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    repair_order = relationship("RepairOrder", backref="boards")