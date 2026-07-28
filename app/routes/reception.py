from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
import os
import shutil
from datetime import datetime
import uuid
import io
from pydantic import BaseModel, Field
from sqlalchemy import text
from app.database import get_db
from app.models import Customer, Device, RepairOrder, User
from app.models.repair_order import OrderStatus
from app.models.status_history import StatusHistory
from app.models.attachment import Attachment
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
# مدل‌های Pydantic
# ============================================
class StatusUpdateRequest(BaseModel):
    """مدل درخواست تغییر وضعیت"""
    status: str = Field(..., description="وضعیت جدید به صورت فارسی")
    reason: Optional[str] = Field(None, description="دلیل تغییر وضعیت")

class SearchParams(BaseModel):
    """مدل پارامترهای جستجو"""
    q: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

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
    """فرمت کردن پاسخ پرونده"""
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
        "device_brand": order.device.brand if order.device else None,
        "device_model": order.device.model if order.device else None,
        "device_part_number": order.device.part_number if order.device else None,
        "device_serial_number": order.device.serial_number if order.device else None
    }

# ============================================
# 1. ثبت مشتری جدید
# ============================================
@router.post("/customers", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ثبت مشتری جدید - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"ثبت مشتری جدید توسط: {current_user.username}")
    
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

# ============================================
# 2. ثبت دستگاه جدید
# ============================================
@router.post("/devices", response_model=DeviceResponse, status_code=http_status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ثبت دستگاه جدید - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"ثبت دستگاه جدید توسط: {current_user.username}")
    
    # بررسی تکراری بودن سریال نامبر
    existing = db.query(Device).filter(Device.serial_number == device.serial_number).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="سریال نامبر قبلاً ثبت شده است"
        )
    
    # بررسی وجود مشتری (در صورت مشخص بودن)
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

# ============================================
# 3. آپلود عکس دستگاه
# ============================================
@router.post("/devices/{device_id}/upload-photo")
def upload_device_photo(
    device_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    آپلود عکس دستگاه - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"آپلود عکس دستگاه {device_id} توسط: {current_user.username}")
    
    # بررسی وجود دستگاه
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="دستگاه مورد نظر یافت نشد"
        )
    
    # بررسی حجم فایل
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"حجم فایل بیش از حد مجاز ({settings.max_file_size // (1024*1024)} مگابایت) است"
        )
    
    try:
        # ایجاد پوشه
        upload_dir = os.path.join(settings.upload_dir, "photos", str(device_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # ذخیره فایل
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # بروزرسانی مسیر عکس در دیتابیس
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

# ============================================
# 4. ایجاد پرونده تعمیر جدید
# ============================================
@router.post("/repair-orders", response_model=RepairOrderResponse, status_code=http_status.HTTP_201_CREATED)
def create_repair_order(
    order: RepairOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    ایجاد پرونده تعمیر جدید - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"ایجاد پرونده جدید توسط: {current_user.username}")
    
    try:
        # بررسی وجود مشتری
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="مشتری مورد نظر یافت نشد"
            )
        
        # بررسی وجود دستگاه
        device = db.query(Device).filter(Device.id == order.device_id).first()
        if not device:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="دستگاه مورد نظر یافت نشد"
            )
        
        # ایجاد کد رهگیری
        tracking_code = generate_tracking_code()
        
        # ایجاد پرونده
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

# ============================================
# 5. دریافت لیست پرونده‌ها
# ============================================
@router.get("/repair-orders")
def get_repair_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست پرونده‌ها - عمومی (بدون نیاز به احراز هویت)
    """
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
        
        orders = query.order_by(RepairOrder.created_at.desc()).offset(skip).limit(limit).all()
        
        result = [format_order_response(order) for order in orders]
        return result
    
    except Exception as e:
        logger.error(f"خطا در دریافت لیست پرونده‌ها: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در دریافت اطلاعات"
        )

# ============================================
# 6. جستجوی پیشرفته پرونده‌ها
# ============================================
@router.get("/repair-orders/search")
def search_repair_orders(
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    جستجوی پیشرفته پرونده‌ها - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 7. دریافت جزئیات یک پرونده
# ============================================
@router.get("/repair-orders/{order_id}")
def get_repair_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    دریافت جزئیات یک پرونده - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 8. جستجوی مشتریان
# ============================================
@router.get("/customers/search", response_model=List[CustomerResponse])
def search_customers(
    q: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    جستجوی مشتریان - عمومی (بدون نیاز به احراز هویت)
    """
    try:
        query = db.query(Customer)
        
        if q:
            query = query.filter(Customer.name.ilike(f"%{q}%"))
        
        if phone:
            query = query.filter(Customer.phone.ilike(f"%{phone}%"))
        
        return query.limit(20).all()
    
    except Exception as e:
        logger.error(f"خطا در جستجوی مشتریان: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در جستجوی اطلاعات"
        )

# ============================================
# 9. جستجوی دستگاه‌ها
# ============================================
@router.get("/devices/search", response_model=List[DeviceResponse])
def search_devices(
    q: Optional[str] = None,
    serial: Optional[str] = None,
    part_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    جستجوی دستگاه‌ها - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 10. تغییر وضعیت پرونده (فقط فنی و ادمین)
# ============================================
@router.put("/repair-orders/{order_id}/status")
def update_order_status(
    order_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_technical_user)
):
    """
    تغییر وضعیت پرونده - فقط نقش فنی و ادمین
    """
    logger.info(f"تغییر وضعیت پرونده {order_id} توسط: {current_user.username}")
    
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        # تبدیل وضعیت فارسی به Enum
        new_status = get_status_enum(request.status)
        old_status = order.status
        
        # جلوگیری از تغییر وضعیت به وضعیت قبلی
        if old_status == new_status:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"پرونده در حال حاضر در وضعیت '{request.status}' است"
            )
        
        # بروزرسانی وضعیت
        order.status = new_status
        
        # بروزرسانی تاریخ‌های مربوطه
        if new_status == OrderStatus.WAITING_TECHNICAL:
            order.technical_review_date = datetime.now()
        elif new_status == OrderStatus.DIAGNOSING:
            order.diagnosis_date = datetime.now()
        elif new_status == OrderStatus.REPAIRING:
            order.repair_start_date = datetime.now()
        elif new_status == OrderStatus.TESTING:
            order.repair_complete_date = datetime.now()
        elif new_status == OrderStatus.READY_DELIVERY:
            # تاریخ کنترل نهایی
            pass
        elif new_status == OrderStatus.DELIVERED:
            order.final_delivery_date = datetime.now()
        
        # ثبت تاریخچه تغییرات
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

# ============================================
# 11. دریافت تاریخچه تغییرات
# ============================================
@router.get("/repair-orders/{order_id}/history")
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    دریافت تاریخچه تغییرات پرونده - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 12. دریافت آمار پرونده‌ها برای داشبورد
# ============================================
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    دریافت آمار پرونده‌ها - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 13. خروجی Excel
# ============================================
@router.get("/repair-orders/export/excel")
def export_repair_orders_excel(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    خروجی Excel از پرونده‌ها - عمومی (بدون نیاز به احراز هویت)
    """
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
        
        # ایجاد فایل Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "پرونده‌های تعمیرات"
        
        # تنظیم هدرها
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
        
        # پر کردن داده‌ها
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
        
        # تنظیم عرض ستون‌ها
        column_widths = [10, 20, 20, 25, 20, 25, 20, 35, 20, 20, 25, 25, 40, 10]
        for col, width in enumerate(column_widths, 1):
            col_letter = chr(64 + col) if col <= 26 else chr(64 + (col-1)//26) + chr(64 + (col-1)%26 + 1)
            ws.column_dimensions[col_letter].width = width
        
        # ذخیره در حافظه
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

# ============================================
# 14. آپلود فایل برای پرونده
# ============================================
@router.post("/repair-orders/{order_id}/upload")
async def upload_file(
    order_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    آپلود فایل ضمیمه برای پرونده - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"آپلود فایل برای پرونده {order_id} توسط: {current_user.username}")
    
    try:
        order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="پرونده مورد نظر یافت نشد"
            )
        
        # بررسی حجم فایل
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"حجم فایل بیش از حد مجاز ({settings.max_file_size // (1024*1024)} مگابایت) است"
            )
        
        # ایجاد پوشه
        upload_dir = os.path.join(settings.upload_dir, "attachments", str(order_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # ذخیره فایل
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        file_size = 0
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                buffer.write(chunk)
        
        # تشخیص نوع فایل
        file_type = "document"
        if file.content_type and file.content_type.startswith("image/"):
            file_type = "photo"
        elif file.content_type and file.content_type.startswith("video/"):
            file_type = "video"
        elif file.content_type and file.content_type == "application/pdf":
            file_type = "pdf"
        
        # ثبت در دیتابیس
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

# ============================================
# 15. دریافت لیست فایل‌های یک پرونده
# ============================================
@router.get("/repair-orders/{order_id}/attachments")
def get_attachments(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    دریافت لیست فایل‌های ضمیمه - عمومی (بدون نیاز به احراز هویت)
    """
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

# ============================================
# 16. حذف فایل ضمیمه
# ============================================
@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_reception_user)
):
    """
    حذف فایل ضمیمه - نیاز به نقش پذیرش یا ادمین
    """
    logger.info(f"حذف فایل {attachment_id} توسط: {current_user.username}")
    
    try:
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="فایل مورد نظر یافت نشد"
            )
        
        # حذف فایل از دیسک
        file_path = os.path.join(settings.upload_dir, attachment.file_path.lstrip("/uploads/"))
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # حذف از دیتابیس
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

# ============================================
# 17. API تست
# ============================================
@router.get("/ping")
def ping():
    """API تست برای بررسی سلامت"""
    return {
        "message": "pong",
        "status": "API is working!",
        "timestamp": datetime.now().isoformat()
    }
@router.get("/ping", operation_id="ping_api")
def ping(db: Session = Depends(get_db)):
    """API تست برای بررسی سلامت"""
    try:
        # ✅ استفاده از text()
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