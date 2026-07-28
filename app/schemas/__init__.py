from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============================================
# مدل‌های مشتری (Customer)
# ============================================
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="نام مشتری")
    company: Optional[str] = Field(None, max_length=100, description="شرکت")
    phone: str = Field(..., min_length=1, max_length=20, description="شماره تماس")
    phone_alternative: Optional[str] = Field(None, max_length=20, description="شماره تماس جایگزین")
    email: Optional[EmailStr] = Field(None, description="ایمیل")
    address: Optional[str] = Field(None, max_length=500, description="آدرس")

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============================================
# مدل‌های دستگاه (Device)
# ============================================
class PhysicalCondition(str, Enum):
    HEALTHY = "سالم"
    BROKEN = "شکستگی"
    BURN = "آثار سوختگی"
    TAMPERED = "دستکاری شده"
    CORRODED = "خوردگی"
    WATER_DAMAGE = "آب خوردگی"

class DeviceBase(BaseModel):
    brand: str = Field(..., max_length=100, description="برند")
    model: str = Field(..., max_length=100, description="مدل")
    part_number: str = Field(..., max_length=100, description="پارت نامبر")
    serial_number: str = Field(..., max_length=100, description="سریال نامبر")
    firmware_version: Optional[str] = Field(None, max_length=50, description="نسخه Firmware")
    physical_condition: Optional[PhysicalCondition] = Field(None, description="وضعیت ظاهری")
    physical_condition_notes: Optional[str] = Field(None, description="توضیحات وضعیت ظاهری")

class DeviceCreate(DeviceBase):
    customer_id: Optional[int] = Field(None, description="شناسه مشتری")

class DeviceResponse(DeviceBase):
    id: int
    photo_paths: List[str] = []
    customer_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============================================
# مدل‌های پرونده تعمیر (Repair Order)
# ============================================
class OrderStatus(str, Enum):
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

class RepairOrderBase(BaseModel):
    customer_id: int = Field(..., description="شناسه مشتری")
    device_id: int = Field(..., description="شناسه دستگاه")
    customer_complaint: Optional[str] = Field(None, description="شرح مشکل از زبان مشتری")
    notes: Optional[str] = Field(None, description="یادداشت‌ها")
    priority: int = Field(0, ge=0, le=2, description="اولویت: 0=عادی، 1=مهم، 2=اورژانسی")

class RepairOrderCreate(RepairOrderBase):
    pass

class RepairOrderResponse(RepairOrderBase):
    id: int
    tracking_code: str
    status: OrderStatus
    reception_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True