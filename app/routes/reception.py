from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status as http_status, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
import os
import shutil
from datetime import datetime
import uuid
import io
import json
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
from pydantic import ValidationError
from app.database import get_db
from app.models import (
    Customer, Device, RepairOrder, User, StatusHistory, Attachment,
    Site, SiteType, Panel, Board, BoardType, OrderStatus
)
from app.schemas import (
    CustomerCreate, CustomerResponse,
    DeviceCreate, DeviceResponse,
    RepairOrderCreate, RepairOrderResponse
)
from app.config import settings
from app.auth import (
    get_current_user, 
    get_current_active_user,
    get_current_admin_user,
    get_current_technical_user,
    get_current_reception_user
)
from app.schemas import PhysicalCondition

# کتابخانه‌های Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reception", tags=["پذیرش"])

# ============================================
# مدل‌های Pydantic برای APIهای جدید
# ============================================

class SiteCreate(BaseModel):
    name: str
    type: str
    address: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    building_name: Optional[str] = None
    building_manager: Optional[str] = None
    manager_phone: Optional[str] = None
    lobby_phone: Optional[str] = None
    responsible_name: Optional[str] = None
    responsible_position: Optional[str] = None
    responsible_phone: Optional[str] = None
    customer_id: int

class SiteResponse(BaseModel):
    id: int
    name: str
    type: str
    address: Optional[str]
    location: Optional[str]
    description: Optional[str]
    building_name: Optional[str]
    building_manager: Optional[str]
    manager_phone: Optional[str]
    lobby_phone: Optional[str]
    responsible_name: Optional[str]
    responsible_position: Optional[str]
    responsible_phone: Optional[str]
    customer_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PanelCreate(BaseModel):
    brand: str
    model: str
    serial_number: str
    part_number: str
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    loops_count: int = 0
    zones_count: int = 0
    installation_year: Optional[int] = None

class PanelResponse(BaseModel):
    id: int
    brand: str
    model: str
    serial_number: str
    part_number: str
    firmware_version: Optional[str]
    hardware_version: Optional[str]
    loops_count: int
    zones_count: int
    installation_year: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BoardCreate(BaseModel):
    board_type: str
    part_number: str
    serial_number: str
    revision: Optional[str] = None
    description: Optional[str] = None

class RepairOrderV2Create(BaseModel):
    customer_id: int
    site_id: Optional[int] = None
    panel_id: int
    sender_name: Optional[str] = None
    sender_position: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_landline: Optional[str] = None
    delivery_method: Optional[str] = None
    courier_company: Optional[str] = None
    courier_tracking: Optional[str] = None
    physical_damages: List[str] = []
    physical_description: Optional[str] = None
    accessories: List[str] = []
    accessories_description: Optional[str] = None
    customer_complaint: str
    boards: List[dict] = []

# ============================================
# مدل برای تغییر وضعیت
# ============================================
class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None

# ============================================
# توابع کمکی
# ============================================
def generate_tracking_code() -> str:
    """تولید کد رهگیری یکتا"""
    return f"SR-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

def get_status_enum(status_str: str) -> OrderStatus:
    """تبدیل وضعیت فارسی به Enum"""
    status_map = {
        "ثبت شده": OrderStatus.REGISTERED,
        "در انتظار بررسی فنی": OrderStatus.WAITING_TECHNICAL,
        "در حال عیب‌یابی": OrderStatus.DIAGNOSING,
        "در انتظار تایید مشتری": OrderStatus.WAITING_APPROVAL,
        "در حال تعمیر": OrderStatus.REPAIRING,
        "در حال تست": OrderStatus.TESTING,
        "کنترل نهایی": OrderStatus.FINAL_CONTROL,
        "آماده تحویل": OrderStatus.READY_DELIVERY,
        "تحویل شده": OrderStatus.DELIVERED,
        "مختومه بدون تعمیر": OrderStatus.CLOSED_NO_REPAIR
    }
    if status_str not in status_map:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"وضعیت '{status_str}' معتبر نیست. وضعیت‌های مجاز: {', '.join(status_map.keys())}"
        )
    return status_map[status_str]

def format_order_response(order: RepairOrder) -> dict:
    return {
        "id": order.id,
        "tracking_code": order.tracking_code,
        "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
        "reception_date": order.reception_date,
        "technical_review_date": order.technical_review_date,
        "diagnosis_date": order.diagnosis_date,
        "repair_start_date": order.repair_start_date,
        "repair_complete_date": order.repair_complete_date,
        "final_delivery_date": order.final_delivery_date,
        "customer_complaint": order.customer_complaint,
        "notes": order.notes,
        "priority": order.priority,
        "created_at": order.created_at,
        "customer_name": order.customer.name if order.customer else None,
        "customer_company": order.customer.company if order.customer else None,
        "customer_phone": order.customer.phone if order.customer else None,
        "customer_address": order.customer.address if order.customer else None,
        # ✅ تغییر از device به panel
        "device_brand": order.panel.brand if order.panel else None,
        "device_model": order.panel.model if order.panel else None,
        "device_part_number": order.panel.part_number if order.panel else None,
        "device_serial_number": order.panel.serial_number if order.panel else None
    }

# ============================================
# بخش 1: APIهای قدیمی (حفظ شده)
# ============================================

# --------------------------------------------
# 1. ثبت مشتری جدید
# --------------------------------------------
@router.post("/customers", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """ثبت مشتری جدید - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"ثبت مشتری جدید توسط: {current_user.username}")
    
    existing = db.query(Customer).filter(Customer.phone == customer.phone).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="شماره تماس قبلاً ثبت شده است"
        )
    
    if customer.email:
        existing = db.query(Customer).filter(Customer.email == customer.email).first()
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="ایمیل قبلاً ثبت شده است"
            )
    
    try:
        db_customer = Customer(**customer.model_dump())
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        logger.info(f"✅ مشتری جدید ثبت شد: {db_customer.name} - {db_customer.phone}")
        return db_customer
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت مشتری: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت مشتری: {str(e)}"
        )

# --------------------------------------------
# 2. ثبت دستگاه جدید
# --------------------------------------------
@router.post("/devices", response_model=DeviceResponse, status_code=http_status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """ثبت دستگاه جدید - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"ثبت دستگاه جدید توسط: {current_user.username}")
    
    existing = db.query(Device).filter(Device.serial_number == device.serial_number).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="سریال نامبر قبلاً ثبت شده است"
        )
    
    if device.customer_id:
        customer = db.query(Customer).filter(Customer.id == device.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری مورد نظر یافت نشد"
            )
    
    try:
        db_device = Device(**device.model_dump())
        db.add(db_device)
        db.commit()
        db.refresh(db_device)
        logger.info(f"✅ دستگاه جدید ثبت شد: {db_device.brand} {db_device.model} - SN: {db_device.serial_number}")
        return db_device
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت دستگاه: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت دستگاه: {str(e)}"
        )

# --------------------------------------------
# 3. آپلود عکس دستگاه
# --------------------------------------------
@router.post("/devices/{device_id}/upload-photo")
def upload_device_photo(
    device_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """آپلود عکس دستگاه - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"آپلود عکس دستگاه {device_id} توسط: {current_user.username}")
    
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="دستگاه مورد نظر یافت نشد"
        )
    
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"حجم فایل بیش از حد مجاز ({settings.max_file_size // (1024*1024)} مگابایت) است"
        )
    
    try:
        upload_dir = os.path.join(settings.upload_dir, "photos", str(device_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if device.photo_paths is None:
            device.photo_paths = []
        relative_path = f"/uploads/photos/{device_id}/{unique_filename}"
        device.photo_paths.append(relative_path)
        db.commit()
        
        logger.info(f"✅ عکس دستگاه {device_id} آپلود شد")
        return {"message": "عکس با موفقیت آپلود شد", "path": relative_path}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در آپلود عکس: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در آپلود عکس: {str(e)}"
        )

# --------------------------------------------
# 4. ایجاد پرونده تعمیر جدید (نسخه قدیمی)
# --------------------------------------------
@router.post("/repair-orders", response_model=RepairOrderResponse, status_code=http_status.HTTP_201_CREATED)
def create_repair_order(
    order: RepairOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """ایجاد پرونده تعمیر جدید - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"ایجاد پرونده جدید توسط: {current_user.username}")
    
    try:
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری مورد نظر یافت نشد"
            )
        
        device = db.query(Device).filter(Device.id == order.device_id).first()
        if not device:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="دستگاه مورد نظر یافت نشد"
            )
        
        tracking_code = generate_tracking_code()
        
        db_order = RepairOrder(
            **order.model_dump(),
            tracking_code=tracking_code,
            status=OrderStatus.REGISTERED
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        logger.info(f"✅ پرونده جدید ثبت شد: {db_order.tracking_code}")
        return db_order
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ایجاد پرونده: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد پرونده: {str(e)}"
        )

# --------------------------------------------
# 5. دریافت لیست پرونده‌ها
# --------------------------------------------
@router.get("/repair-orders")
def get_repair_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(RepairOrder).options(
            joinedload(RepairOrder.customer),
            # ❌ device حذف شد - از panel استفاده کن
            joinedload(RepairOrder.panel),
            joinedload(RepairOrder.site)
        )
        
        if status:
            try:
                status_enum = get_status_enum(status)
                query = query.filter(RepairOrder.status == status_enum)
            except HTTPException:
                pass
        
        orders = query.order_by(RepairOrder.created_at.desc()).offset(skip).limit(limit).all()
        result = [format_order_response(order) for order in orders]
        return result
    
    except Exception as e:
        logger.error(f"خطا در دریافت لیست پرونده‌ها: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 6. جستجوی پیشرفته پرونده‌ها
# --------------------------------------------
@router.get("/repair-orders/search")
def search_repair_orders(
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """جستجوی پیشرفته پرونده‌ها - عمومی (بدون نیاز به احراز هویت)"""
    try:
        query = db.query(RepairOrder).join(Customer, RepairOrder.customer_id == Customer.id)\
                                     .join(Device, RepairOrder.device_id == Device.id)
        
        if q:
            q_filter = f"%{q}%"
            query = query.filter(
                (Customer.name.ilike(q_filter)) |
                (Customer.phone.ilike(q_filter)) |
                (RepairOrder.tracking_code.ilike(q_filter)) |
                (Device.serial_number.ilike(q_filter)) |
                (Device.part_number.ilike(q_filter))
            )
        
        if status:
            try:
                status_enum = get_status_enum(status)
                query = query.filter(RepairOrder.status == status_enum)
            except HTTPException:
                pass
        
        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(RepairOrder.created_at >= date_from_parsed)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(RepairOrder.created_at <= date_to_parsed)
            except ValueError:
                pass
        
        results = query.order_by(RepairOrder.created_at.desc()).all()
        return [format_order_response(order) for order in results]
    
    except Exception as e:
        logger.error(f"خطا در جستجوی پرونده‌ها: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# --------------------------------------------
# 7. دریافت جزئیات یک پرونده
# --------------------------------------------
@router.get("/repair-orders/{order_id}")
def get_repair_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت جزئیات یک پرونده - عمومی (بدون نیاز به احراز هویت)"""
    try:
        order = db.query(RepairOrder).options(
            joinedload(RepairOrder.customer),
            joinedload(RepairOrder.device)
        ).filter(RepairOrder.id == order_id).first()
        
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        return format_order_response(order)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در دریافت جزئیات پرونده {order_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 8. جستجوی مشتریان (ساده)
# --------------------------------------------
@router.get("/customers/search", response_model=List[CustomerResponse])
def search_customers_simple(
    q: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """جستجوی مشتریان - عمومی (بدون نیاز به احراز هویت)"""
    try:
        query = db.query(Customer)
        
        if q:
            query = query.filter(
                (Customer.name.ilike(f"%{q}%")) |
                (Customer.company.ilike(f"%{q}%"))
            )
        
        if phone:
            query = query.filter(Customer.phone.ilike(f"%{phone}%"))
        
        return query.limit(20).all()
    
    except Exception as e:
        logger.error(f"خطا در جستجوی مشتریان: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# --------------------------------------------
# 9. جستجوی دستگاه‌ها
# --------------------------------------------
@router.get("/devices/search", response_model=List[DeviceResponse])
def search_devices(
    q: Optional[str] = None,
    serial: Optional[str] = None,
    part_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """جستجوی دستگاه‌ها - عمومی (بدون نیاز به احراز هویت)"""
    try:
        query = db.query(Device)
        
        if q:
            query = query.filter(
                (Device.brand.ilike(f"%{q}%")) | 
                (Device.model.ilike(f"%{q}%"))
            )
        
        if serial:
            query = query.filter(Device.serial_number.ilike(f"%{serial}%"))
        
        if part_number:
            query = query.filter(Device.part_number.ilike(f"%{part_number}%"))
        
        return query.limit(20).all()
    
    except Exception as e:
        logger.error(f"خطا در جستجوی دستگاه‌ها: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# --------------------------------------------
# 10. تغییر وضعیت پرونده
# --------------------------------------------
@router.put("/repair-orders/{order_id}/status")
def update_order_status(
    order_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technical_user)
):
    """تغییر وضعیت پرونده - فقط نقش فنی و ادمین"""
    logger.info(f"تغییر وضعیت پرونده {order_id} توسط: {current_user.username}")
    
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        new_status = get_status_enum(request.status)
        old_status = order.status
        
        if old_status == new_status:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"پرونده در حال حاضر در وضعیت '{request.status}' است"
            )
        
        order.status = new_status
        
        if new_status == OrderStatus.WAITING_TECHNICAL:
            order.technical_review_date = datetime.now()
        elif new_status == OrderStatus.DIAGNOSING:
            order.diagnosis_date = datetime.now()
        elif new_status == OrderStatus.REPAIRING:
            order.repair_start_date = datetime.now()
        elif new_status == OrderStatus.TESTING:
            order.repair_complete_date = datetime.now()
        elif new_status == OrderStatus.READY_DELIVERY:
            pass
        elif new_status == OrderStatus.DELIVERED:
            order.final_delivery_date = datetime.now()
        
        history = StatusHistory(
            repair_order_id=order.id,
            old_status=old_status,
            new_status=new_status,
            reason=request.reason or f"تغییر وضعیت از {old_status.value} به {new_status.value}",
            changed_by=current_user.id,
            operator_name=current_user.full_name
        )
        db.add(history)
        db.commit()
        db.refresh(order)
        
        logger.info(f"✅ وضعیت پرونده {order.tracking_code} از {old_status.value} به {new_status.value} تغییر کرد")
        
        return {
            "message": "وضعیت با موفقیت بروزرسانی شد",
            "order_id": order.id,
            "tracking_code": order.tracking_code,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "reason": request.reason,
            "operator": current_user.full_name
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در تغییر وضعیت پرونده {order_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در تغییر وضعیت: {str(e)}"
        )

# --------------------------------------------
# 11. دریافت تاریخچه تغییرات
# --------------------------------------------
@router.get("/repair-orders/{order_id}/history")
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت تاریخچه تغییرات پرونده - عمومی (بدون نیاز به احراز هویت)"""
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        history = db.query(StatusHistory).filter(
            StatusHistory.repair_order_id == order_id
        ).order_by(StatusHistory.changed_at.desc()).all()
        
        return history
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در دریافت تاریخچه پرونده {order_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 12. دریافت آمار پرونده‌ها
# --------------------------------------------
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """دریافت آمار پرونده‌ها - عمومی (بدون نیاز به احراز هویت)"""
    try:
        total = db.query(RepairOrder).count()
        
        repairing = db.query(RepairOrder).filter(
            RepairOrder.status.in_([
                OrderStatus.WAITING_TECHNICAL,
                OrderStatus.DIAGNOSING,
                OrderStatus.REPAIRING,
                OrderStatus.TESTING,
                OrderStatus.FINAL_CONTROL
            ])
        ).count()
        
        waiting_approval = db.query(RepairOrder).filter(
            RepairOrder.status == OrderStatus.WAITING_APPROVAL
        ).count()
        
        ready_delivery = db.query(RepairOrder).filter(
            RepairOrder.status == OrderStatus.READY_DELIVERY
        ).count()
        
        delivered = db.query(RepairOrder).filter(
            RepairOrder.status == OrderStatus.DELIVERED
        ).count()
        
        closed = db.query(RepairOrder).filter(
            RepairOrder.status == OrderStatus.CLOSED_NO_REPAIR
        ).count()
        
        return {
            "total": total,
            "repairing": repairing,
            "waiting_approval": waiting_approval,
            "ready_delivery": ready_delivery,
            "delivered": delivered,
            "closed": closed,
            "active": total - delivered - closed
        }
    
    except Exception as e:
        logger.error(f"خطا در دریافت آمار: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت آمار"
        )

# --------------------------------------------
# 13. خروجی Excel
# --------------------------------------------
@router.get("/repair-orders/export/excel")
def export_repair_orders_excel(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """خروجی Excel از پرونده‌ها - عمومی (بدون نیاز به احراز هویت)"""
    try:
        query = db.query(RepairOrder).options(
            joinedload(RepairOrder.customer),
            joinedload(RepairOrder.device)
        )
        
        if status:
            try:
                status_enum = get_status_enum(status)
                query = query.filter(RepairOrder.status == status_enum)
            except HTTPException:
                pass
        
        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(RepairOrder.created_at >= date_from_parsed)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(RepairOrder.created_at <= date_to_parsed)
            except ValueError:
                pass
        
        orders = query.order_by(RepairOrder.created_at.desc()).all()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "پرونده‌های تعمیرات"
        
        header_font = Font(name='B Nazanin', size=12, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0D6EFD", end_color="0D6EFD", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        headers = [
            "شناسه", "کد رهگیری", "وضعیت", "تاریخ پذیرش",
            "نام مشتری", "شرکت", "شماره تماس", "آدرس",
            "برند", "مدل", "پارت نامبر", "سریال نامبر",
            "شرح مشکل", "اولویت"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        for row_idx, order in enumerate(orders, 2):
            ws.cell(row=row_idx, column=1, value=order.id)
            ws.cell(row=row_idx, column=2, value=order.tracking_code)
            ws.cell(row=row_idx, column=3, value=order.status.value if hasattr(order.status, 'value') else str(order.status))
            ws.cell(row=row_idx, column=4, value=order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "")
            ws.cell(row=row_idx, column=5, value=order.customer.name if order.customer else "")
            ws.cell(row=row_idx, column=6, value=order.customer.company if order.customer else "")
            ws.cell(row=row_idx, column=7, value=order.customer.phone if order.customer else "")
            ws.cell(row=row_idx, column=8, value=order.customer.address if order.customer else "")
            ws.cell(row=row_idx, column=9, value=order.device.brand if order.device else "")
            ws.cell(row=row_idx, column=10, value=order.device.model if order.device else "")
            ws.cell(row=row_idx, column=11, value=order.device.part_number if order.device else "")
            ws.cell(row=row_idx, column=12, value=order.device.serial_number if order.device else "")
            ws.cell(row=row_idx, column=13, value=order.customer_complaint or "")
            ws.cell(row=row_idx, column=14, value=order.priority or 0)
            
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_idx, column=col).border = thin_border
        
        column_widths = [10, 20, 20, 25, 20, 25, 20, 35, 20, 20, 25, 25, 40, 10]
        for col, width in enumerate(column_widths, 1):
            col_letter = chr(64 + col) if col <= 26 else chr(64 + (col-1)//26) + chr(64 + (col-1)%26 + 1)
            ws.column_dimensions[col_letter].width = width
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"گزارش_پرونده‌ها_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        encoded_filename = filename.encode('utf-8').decode('latin-1', errors='ignore')
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={encoded_filename}"}
        )
    
    except Exception as e:
        logger.error(f"خطا در خروجی Excel: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در ایجاد فایل Excel"
        )

# --------------------------------------------
# 14. آپلود فایل برای پرونده
# --------------------------------------------
@router.post("/repair-orders/{order_id}/upload")
async def upload_file(
    order_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """آپلود فایل ضمیمه برای پرونده - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"آپلود فایل برای پرونده {order_id} توسط: {current_user.username}")
    
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"حجم فایل بیش از حد مجاز ({settings.max_file_size // (1024*1024)} مگابایت) است"
            )
        
        upload_dir = os.path.join(settings.upload_dir, "attachments", str(order_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        file_size = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                buffer.write(chunk)
        
        file_type = "document"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "photo"
        elif file.content_type and file.content_type.startswith("video/"):
            file_type = "video"
        elif file.content_type and file.content_type == "application/pdf":
            file_type = "pdf"
        
        attachment = Attachment(
            file_name=file.filename,
            file_path=f"/uploads/attachments/{order_id}/{unique_filename}",
            file_type=file_type,
            file_size=file_size,
            mime_type=file.content_type,
            description=description,
            repair_order_id=order_id,
            uploaded_by=current_user.id
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        logger.info(f"✅ فایل {file.filename} برای پرونده {order_id} آپلود شد")
        
        return {
            "message": "فایل با موفقیت آپلود شد",
            "attachment_id": attachment.id,
            "file_name": attachment.file_name,
            "file_path": attachment.file_path,
            "file_type": attachment.file_type,
            "file_size": attachment.file_size
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"خطا در آپلود فایل: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در آپلود فایل: {str(e)}"
        )

# --------------------------------------------
# 15. دریافت لیست فایل‌های یک پرونده
# --------------------------------------------
@router.get("/repair-orders/{order_id}/attachments")
def get_attachments(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت لیست فایل‌های ضمیمه - عمومی (بدون نیاز به احراز هویت)"""
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        attachments = db.query(Attachment).filter(
            Attachment.repair_order_id == order_id
        ).order_by(Attachment.uploaded_at.desc()).all()
        
        return attachments
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در دریافت فایل‌های پرونده {order_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 16. حذف فایل ضمیمه
# --------------------------------------------
@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """حذف فایل ضمیمه - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"حذف فایل {attachment_id} توسط: {current_user.username}")
    
    try:
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="فایل مورد نظر یافت نشد"
            )
        
        file_path = os.path.join(settings.upload_dir, attachment.file_path.lstrip("/uploads/"))
        if os.path.exists(file_path):
            os.remove(file_path)
        
        db.delete(attachment)
        db.commit()
        
        logger.info(f"✅ فایل {attachment_id} حذف شد")
        return {"message": "فایل با موفقیت حذف شد"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در حذف فایل {attachment_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف فایل: {str(e)}"
        )

# --------------------------------------------
# 17. API تست
# --------------------------------------------
@router.get("/ping")
def ping(db: Session = Depends(get_db)):
    """API تست برای بررسی سلامت"""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "message": "pong",
            "status": "API is working!",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "message": "pong",
            "status": "Database error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============================================
# بخش 2: APIهای جدید (برای فرم نسخه ۲)
# ============================================

# --------------------------------------------
# 18. جستجوی پیشرفته مشتریان
# --------------------------------------------
@router.get("/customers/search-v2")
def search_customers_advanced(
    q: Optional[str] = None,
    phone: Optional[str] = None,
    id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    جستجوی پیشرفته مشتریان (برای فرم جدید)
    """
    try:
        query = db.query(Customer)
        
        if id:
            customer = query.filter(Customer.id == id).first()
            return customer
        
        if q:
            query = query.filter(
                (Customer.name.ilike(f"%{q}%")) |
                (Customer.company.ilike(f"%{q}%")) |
                (Customer.phone.ilike(f"%{q}%"))
            )
        
        if phone:
            query = query.filter(Customer.phone.ilike(f"%{phone}%"))
        
        return query.limit(20).all()
    
    except Exception as e:
        logger.error(f"خطا در جستجوی مشتریان: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# --------------------------------------------
# 19. دریافت سایت‌های مشتری
# --------------------------------------------
@router.get("/customers/{customer_id}/sites", response_model=List[SiteResponse])
def get_customer_sites(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست محل‌های نصب یک مشتری
    """
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری یافت نشد"
            )
        
        sites = db.query(Site).filter(Site.customer_id == customer_id).all()
        return sites
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در دریافت سایت‌های مشتری {customer_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 20. ثبت محل نصب جدید
# --------------------------------------------
@router.post("/sites", response_model=SiteResponse, status_code=http_status.HTTP_201_CREATED)
def create_site(
    site_data: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ثبت محل نصب جدید
    """
    try:
        customer = db.query(Customer).filter(Customer.id == site_data.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری یافت نشد"
            )
        
        new_site = Site(**site_data.model_dump())
        db.add(new_site)
        db.commit()
        db.refresh(new_site)
        
        logger.info(f"✅ محل نصب جدید ثبت شد: {new_site.name} - مشتری: {customer.name}")
        return new_site
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت محل نصب: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت محل نصب: {str(e)}"
        )

# --------------------------------------------
# 21. ثبت پنل جدید
# --------------------------------------------
@router.post("/panels", response_model=PanelResponse, status_code=http_status.HTTP_201_CREATED)
def create_panel(
    panel_data: PanelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ثبت پنل جدید
    """
    try:
        existing = db.query(Panel).filter(Panel.serial_number == panel_data.serial_number).first()
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="سریال نامبر قبلاً ثبت شده است"
            )
        
        new_panel = Panel(**panel_data.model_dump())
        db.add(new_panel)
        db.commit()
        db.refresh(new_panel)
        
        logger.info(f"✅ پنل جدید ثبت شد: {new_panel.brand} {new_panel.model} - SN: {new_panel.serial_number}")
        return new_panel
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت پنل: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت پنل: {str(e)}"
        )

# --------------------------------------------
# 22. جستجوی پنل‌ها
# --------------------------------------------
@router.get("/panels/search")
def search_panels(
    q: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    جستجوی پنل‌ها
    """
    try:
        query = db.query(Panel)
        
        if q:
            if type == "serial":
                query = query.filter(Panel.serial_number.ilike(f"%{q}%"))
            elif type == "part":
                query = query.filter(Panel.part_number.ilike(f"%{q}%"))
            else:
                query = query.filter(
                    (Panel.brand.ilike(f"%{q}%")) |
                    (Panel.model.ilike(f"%{q}%")) |
                    (Panel.serial_number.ilike(f"%{q}%")) |
                    (Panel.part_number.ilike(f"%{q}%"))
                )
        
        return query.limit(20).all()
    
    except Exception as e:
        logger.error(f"خطا در جستجوی پنل‌ها: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# --------------------------------------------
# 23. دریافت پنل با ID
# --------------------------------------------
@router.get("/panels/{panel_id}", response_model=PanelResponse)
def get_panel(
    panel_id: int,
    db: Session = Depends(get_db)
):
    """
    دریافت اطلاعات یک پنل
    """
    try:
        panel = db.query(Panel).filter(Panel.id == panel_id).first()
        if not panel:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پنل یافت نشد"
            )
        return panel
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در دریافت پنل {panel_id}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# --------------------------------------------
# 24. ثبت پرونده نسخه ۲ (با تمام اطلاعات جدید)
# --------------------------------------------
@router.post("/repair-orders-v2", status_code=http_status.HTTP_201_CREATED)
async def create_repair_order_v2(
    data: str = Form(...),
    photos: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ثبت پرونده جدید با تمام اطلاعات (نسخه ۲)
    """
    try:
        order_data = json.loads(data)
        logger.info(f"ثبت پرونده نسخه ۲ توسط: {current_user.username}")
        
        customer = db.query(Customer).filter(Customer.id == order_data.get('customer_id')).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری یافت نشد"
            )
        
        panel = db.query(Panel).filter(Panel.id == order_data.get('panel_id')).first()
        if not panel:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پنل یافت نشد"
            )
        
        site_id = order_data.get('site_id')
        if site_id:
            site = db.query(Site).filter(Site.id == site_id).first()
            if not site:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="محل نصب یافت نشد"
                )
        
        tracking_code = generate_tracking_code()
        
        repair_order = RepairOrder(
            tracking_code=tracking_code,
            status=OrderStatus.REGISTERED,
            customer_id=order_data.get('customer_id'),
            site_id=order_data.get('site_id'),
            panel_id=order_data.get('panel_id'),
            sender_name=order_data.get('sender_name'),
            sender_position=order_data.get('sender_position'),
            sender_phone=order_data.get('sender_phone'),
            sender_landline=order_data.get('sender_landline'),
            delivery_method=order_data.get('delivery_method'),
            courier_company=order_data.get('courier_company'),
            courier_tracking=order_data.get('courier_tracking'),
            physical_damages=order_data.get('physical_damages', []),
            physical_description=order_data.get('physical_description'),
            accessories=order_data.get('accessories', []),
            accessories_description=order_data.get('accessories_description'),
            customer_complaint=order_data.get('customer_complaint'),
            operator_name=current_user.full_name,
            priority=0
        )
        
        db.add(repair_order)
        db.flush()
        
        boards_data = order_data.get('boards', [])
        for board_data in boards_data:
            board = Board(
                board_type=board_data.get('type'),
                part_number=board_data.get('part_number'),
                serial_number=board_data.get('serial_number'),
                revision=board_data.get('revision'),
                repair_order_id=repair_order.id
            )
            db.add(board)
        
        uploaded_photos = []
        if photos:
            upload_dir = os.path.join(settings.upload_dir, "photos", str(repair_order.id))
            os.makedirs(upload_dir, exist_ok=True)
            
            for photo in photos:
                file_extension = os.path.splitext(photo.filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)
                
                relative_path = f"/uploads/photos/{repair_order.id}/{unique_filename}"
                uploaded_photos.append(relative_path)
                
                attachment = Attachment(
                    file_name=photo.filename,
                    file_path=relative_path,
                    file_type="photo",
                    file_size=os.path.getsize(file_path),
                    mime_type=photo.content_type,
                    is_physical_damage=True,
                    repair_order_id=repair_order.id,
                    uploaded_by=current_user.id
                )
                db.add(attachment)
        
        history = StatusHistory(
            repair_order_id=repair_order.id,
            old_status=None,
            new_status=OrderStatus.REGISTERED,
            reason="ثبت پرونده جدید",
            operator_name=current_user.full_name,
            changed_by=current_user.id
        )
        db.add(history)
        
        db.commit()
        db.refresh(repair_order)
        
        logger.info(f"✅ پرونده نسخه ۲ ثبت شد: {repair_order.tracking_code}")
        
        return {
            "id": repair_order.id,
            "tracking_code": repair_order.tracking_code,
            "status": repair_order.status.value,
            "message": "پرونده با موفقیت ثبت شد",
            "photos_count": len(uploaded_photos),
            "boards_count": len(boards_data)
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت پرونده نسخه ۲: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت پرونده: {str(e)}"
        )
@router.post("/customers", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """ثبت مشتری جدید - نیاز به نقش پذیرش یا ادمین"""
    logger.info(f"ثبت مشتری جدید توسط: {current_user.username}")
    
    try:
        # بررسی تکراری بودن شماره تماس
        existing = db.query(Customer).filter(Customer.phone == customer.phone).first()
        if existing:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="شماره تماس قبلاً ثبت شده است"
            )
        
        # بررسی تکراری بودن ایمیل (در صورت وجود)
        if customer.email:
            existing = db.query(Customer).filter(Customer.email == customer.email).first()
            if existing:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="ایمیل قبلاً ثبت شده است"
                )
        
        db_customer = Customer(**customer.model_dump())
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        logger.info(f"✅ مشتری جدید ثبت شد: {db_customer.name} - {db_customer.phone}")
        return db_customer
        
    except HTTPException:
        db.rollback()
        raise
    except ValidationError as e:
        db.rollback()
        # ✅ ارسال خطاهای واضح
        errors = []
        for error in e.errors():
            field = error['loc'][0]
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors
        )
    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ثبت مشتری: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ثبت مشتری: {str(e)}"
        )
