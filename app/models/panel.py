from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Panel(Base):
    __tablename__ = "panels"
    
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    part_number = Column(String(100), nullable=False, index=True)
    firmware_version = Column(String(50), nullable=True)
    hardware_version = Column(String(50), nullable=True)
    loops_count = Column(Integer, default=0)
    zones_count = Column(Integer, default=0)
    installation_year = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
