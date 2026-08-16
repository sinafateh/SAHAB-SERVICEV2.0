from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowTransferRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    to_department: Optional[str] = Field(default=None, max_length=50)
    stage: str = Field(..., min_length=2, max_length=50)
    note: Optional[str] = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class WorkflowRecipientChangeRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    to_department: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")


class WorkflowRejectRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class WorkflowActionRequest(BaseModel):
    action: str = Field(..., min_length=2, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=4000)
    quoted_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    approved: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class TechnicalTimingRequest(BaseModel):
    stage: str = Field(..., min_length=2, max_length=50)
    note: Optional[str] = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class WorkflowStageResponse(BaseModel):
    code: str
    label: str
    department: str


class WorkflowTransitionResponse(BaseModel):
    transition_id: int
    repair_order_id: int
    from_user_id: int
    from_user_name: Optional[str] = None
    to_user_id: int
    to_user_name: Optional[str] = None
    from_department: Optional[str] = None
    to_department: Optional[str] = None
    action: str
    stage: Optional[str] = None
    note: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    is_received: bool
    received_by: Optional[int] = None
    received_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowTaskResponse(WorkflowTransitionResponse):
    pass
