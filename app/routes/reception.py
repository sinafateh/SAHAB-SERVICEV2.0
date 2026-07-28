from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
import os
import shutil
from datetime import datetime
import uuid
import io
from pydantic import BaseModel

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
from app.auth import get_current_user

# کتابخانه‌های Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

router = APIRouter(prefix="/reception", tags=["پذیرش"])

# ============================================
# مدل برای تغییر وضعیت
# ============================================
class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None

# ============================================
# 1. ثبت مشتری جدید (نیاز به احراز هویت)
# ============================================
@router.post("/customers", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Customer).filter(Customer.phone == customer.phone).first()
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="شماره تماس قبلاً ثبت شده است"
        )
    
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

# ============================================
# 2. ثبت دستگاه جدید (نیاز به احراز هویت)
# ============================================
@router.post("/devices", response_model=DeviceResponse, status_code=http_status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    db_device = Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

# ============================================
# 3. آپلود عکس دستگاه (نیاز به احراز هویت)
# ============================================
@router.post("/devices/{device_id}/upload-photo")
def upload_device_photo(
    device_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="دستگاه مورد نظر یافت نشد"
        )
    
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
    
    return {"message": "عکس با موفقیت آپلود شد", "path": relative_path}

# ============================================
# 4. ایجاد پرونده تعمیر جدید (نیاز به احراز هویت)
# ============================================
@router.post("/repair-orders", response_model=RepairOrderResponse, status_code=http_status.HTTP_201_CREATED)
def create_repair_order(
    order: RepairOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    tracking_code = f"SR-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    
    db_order = RepairOrder(
        **order.model_dump(),
        tracking_code=tracking_code,
        status=OrderStatus.REGISTERED
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

# ============================================
# 5. دریافت لیست پرونده‌ها (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders")
def get_repair_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """دریافت لیست پرونده‌ها - بدون نیاز به احراز هویت"""
    query = db.query(RepairOrder).options(
        joinedload(RepairOrder.customer),
        joinedload(RepairOrder.device)
    )
    
    if status:
        try:
            status_enum = OrderStatus[status]
            query = query.filter(RepairOrder.status == status_enum)
        except KeyError:
            pass
    
    orders = query.order_by(RepairOrder.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for order in orders:
        result.append({
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
        })
    
    return result

# ============================================
# 6. جستجوی پیشرفته (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders/search")
def search_repair_orders(
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """جستجوی پرونده‌ها - بدون نیاز به احراز هویت"""
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
            status_enum = OrderStatus[status]
            query = query.filter(RepairOrder.status == status_enum)
        except KeyError:
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
    
    formatted_results = []
    for order in results:
        formatted_results.append({
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
        })
    
    return formatted_results

# ============================================
# 7. دریافت جزئیات یک پرونده (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders/{order_id}")
def get_repair_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت جزئیات یک پرونده - بدون نیاز به احراز هویت"""
    order = db.query(RepairOrder).options(
        joinedload(RepairOrder.customer),
        joinedload(RepairOrder.device)
    ).filter(RepairOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="پرونده مورد نظر یافت نشد"
        )
    
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
# 8. جستجوی مشتریان (عمومی - بدون احراز هویت)
# ============================================
@router.get("/customers/search", response_model=List[CustomerResponse])
def search_customers(
    q: Optional[str] = None,
    phone: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    
    if q:
        query = query.filter(Customer.name.ilike(f"%{q}%"))
    
    if phone:
        query = query.filter(Customer.phone.ilike(f"%{phone}%"))
    
    return query.limit(20).all()

# ============================================
# 9. جستجوی دستگاه‌ها (عمومی - بدون احراز هویت)
# ============================================
@router.get("/devices/search", response_model=List[DeviceResponse])
def search_devices(
    q: Optional[str] = None,
    serial: Optional[str] = None,
    part_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Device)
    
    if q:
        query = query.filter(
            Device.brand.ilike(f"%{q}%") | 
            Device.model.ilike(f"%{q}%")
        )
    
    if serial:
        query = query.filter(Device.serial_number.ilike(f"%{serial}%"))
    
    if part_number:
        query = query.filter(Device.part_number.ilike(f"%{part_number}%"))
    
    return query.limit(20).all()

# ============================================
# 10. تغییر وضعیت پرونده (نیاز به احراز هویت)
# ============================================
@router.put("/repair-orders/{order_id}/status")
def update_order_status(
    order_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="پرونده مورد نظر یافت نشد"
        )
    
    try:
        new_status = OrderStatus[request.status]
    except KeyError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"وضعیت '{request.status}' معتبر نیست"
        )
    
    old_status = order.status
    order.status = new_status
    
    if new_status == OrderStatus.WAITING_TECHNICAL:
        order.technical_review_date = datetime.now()
    
    history = StatusHistory(
        repair_order_id=order.id,
        old_status=old_status,
        new_status=new_status,
        reason=request.reason or f"تغییر وضعیت از {old_status} به {new_status}",
        changed_by=current_user.id,
        operator_name=current_user.full_name
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    
    return {
        "message": "وضعیت با موفقیت بروزرسانی شد",
        "order_id": order.id,
        "old_status": old_status,
        "new_status": new_status,
        "reason": request.reason,
        "operator": current_user.full_name
    }

# ============================================
# 11. دریافت تاریخچه تغییرات (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders/{order_id}/history")
def get_order_history(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت تاریخچه تغییرات - بدون نیاز به احراز هویت"""
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

# ============================================
# 12. دریافت آمار پرونده‌ها برای داشبورد (عمومی - بدون احراز هویت)
# ============================================
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """دریافت آمار پرونده‌ها - بدون نیاز به احراز هویت"""
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

# ============================================
# 13. خروجی Excel (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders/export/excel")
def export_repair_orders_excel(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """خروجی Excel - بدون نیاز به احراز هویت"""
    query = db.query(RepairOrder).options(
        joinedload(RepairOrder.customer),
        joinedload(RepairOrder.device)
    )
    
    if status:
        try:
            status_enum = OrderStatus[status]
            query = query.filter(RepairOrder.status == status_enum)
        except KeyError:
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
    
    from datetime import datetime as dt
    filename = f"گزارش_پرونده‌ها_{dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = filename.encode('utf-8').decode('latin-1', errors='ignore')
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={encoded_filename}"}
    )

# ============================================
# 14. آپلود فایل برای پرونده (نیاز به احراز هویت)
# ============================================
from fastapi import UploadFile, File, Form

@router.post("/repair-orders/{order_id}/upload")
async def upload_file(
    order_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(RepairOrder).filter(RepairOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="پرونده مورد نظر یافت نشد"
        )
    
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    upload_dir = os.path.join(settings.upload_dir, "attachments", str(order_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"حجم فایل بیش از حد مجاز (10 مگابایت) است"
                    )
                buffer.write(chunk)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در آپلود فایل: {str(e)}"
        )
    
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
    
    return {
        "message": "فایل با موفقیت آپلود شد",
        "attachment_id": attachment.id,
        "file_name": attachment.file_name,
        "file_path": attachment.file_path,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size
    }

# ============================================
# 15. دریافت لیست فایل‌های یک پرونده (عمومی - بدون احراز هویت)
# ============================================
@router.get("/repair-orders/{order_id}/attachments")
def get_attachments(
    order_id: int,
    db: Session = Depends(get_db)
):
    """دریافت لیست فایل‌های ضمیمه - بدون نیاز به احراز هویت"""
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

# ============================================
# 16. حذف فایل ضمیمه (نیاز به احراز هویت)
# ============================================
@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    
    return {"message": "فایل با موفقیت حذف شد"}

# ============================================
# 17. API تست (عمومی - بدون احراز هویت)
# ============================================
@router.get("/ping")
def ping():
    """API تست برای بررسی سلامت"""
    return {"message": "pong", "status": "API is working!"}