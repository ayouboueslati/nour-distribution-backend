from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

# Enums
class OrderStatusEnum(str, Enum):
    EN_ATTENTE = "en_attente"
    EN_TRAITEMENT = "en_traitement"
    CONFIRME = "confirme"
    ANNULE = "annule"

# Order Item Schemas
class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)

class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    discount_percent: Optional[float] = Field(None, ge=0, le=100)

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Optional[float] = None
    discount_percent: float
    subtotal: float
    created_at: datetime
    
    # Product details
    product: Optional[dict] = None

# Order Schemas
class OrderCreate(BaseModel):
    client_id: UUID
    items: List[OrderItemCreate]
    shipping_address: Optional[str] = None
    delivery_notes: Optional[str] = None

class OrderFromCart(BaseModel):
    cart_id: UUID
    shipping_address: Optional[str] = None
    delivery_notes: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[OrderStatusEnum] = None
    shipping_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    internal_notes: Optional[str] = None

class OrderPricing(BaseModel):
    """Schema for admin to set pricing"""
    items: List[OrderItemUpdate]  # List of items with prices
    subtotal: float = Field(ge=0)
    shipping_fee: float = Field(default=0.0, ge=0)
    discount: float = Field(default=0.0, ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    total_amount: float = Field(ge=0)

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    order_number: str
    status: OrderStatusEnum
    client_id: UUID
    
    submitted_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    
    subtotal: float
    shipping_fee: float
    discount: float
    tax_amount: float
    total_amount: float
    
    shipping_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    stock_reserved: bool
    reservation_expires_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    items: List[OrderItemResponse] = []
    client: Optional[dict] = None

class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int = 1
    page_size: int = 100

class OrderHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    order_id: UUID
    changed_by: UUID
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    user: Optional[dict] = None