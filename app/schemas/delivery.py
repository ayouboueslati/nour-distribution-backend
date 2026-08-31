from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.delivery import DeliveryStatus

class DeliveryItemBase(BaseModel):
    product_id: UUID
    quantity: int

class DeliveryItemCreate(DeliveryItemBase):
    pass

class DeliveryItemResponse(DeliveryItemBase):
    id: UUID
    product_name: str
    product_sku: str
    
    class Config:
        orm_mode = True

class DeliveryNoteBase(BaseModel):
    notes: Optional[str] = None
    tracking_reference: Optional[str] = None
    carrier_name: Optional[str] = None

class DeliveryNoteCreate(DeliveryNoteBase):
    order_id: UUID
    items: List[DeliveryItemCreate]

class DeliveryNoteResponse(DeliveryNoteBase):
    id: UUID
    delivery_number: str
    status: DeliveryStatus
    order_id: UUID
    client_id: UUID
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    items: List[DeliveryItemResponse]
    created_at: datetime
    # Computed from client relationship — used by the frontend deliveries table
    client_name: Optional[str] = None

    class Config:
        orm_mode = True
