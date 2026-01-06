from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum

class ChargeCategory(str, Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    SALARIES = "salaries"
    MARKETING = "marketing"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class ChargeType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"

class ChargeRecurrence(str, Enum):
    PONCTUEL = "ponctuel"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class ChargeBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    category: ChargeCategory
    date: datetime
    type: ChargeType = ChargeType.VARIABLE
    recurrence: ChargeRecurrence = ChargeRecurrence.PONCTUEL
    validated: bool = False
    supplier: Optional[str] = Field(None, max_length=255)
    receipt_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

class ChargeCreate(ChargeBase):
    pass

class ChargeUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[ChargeCategory] = None
    date: Optional[datetime] = None
    type: Optional[ChargeType] = None
    recurrence: Optional[ChargeRecurrence] = None
    validated: Optional[bool] = None
    supplier: Optional[str] = Field(None, max_length=255)
    receipt_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

class ChargeResponse(ChargeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
