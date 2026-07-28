from app.models.base import Base
from app.models.customer import Customer
from app.models.device import Device, PhysicalCondition
from app.models.user import User
from app.models.repair_order import RepairOrder, OrderStatus
from app.models.status_history import StatusHistory
from app.models.attachment import Attachment

# ✅ export همه مدل‌ها برای استفاده آسان
__all__ = [
    'Base',
    'Customer',
    'Device',
    'PhysicalCondition',
    'User',
    'RepairOrder',
    'OrderStatus',
    'StatusHistory',
    'Attachment'
]