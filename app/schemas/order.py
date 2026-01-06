from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

from app.schemas.client import ClientResponse
from app.schemas.product import ProductPublicResponse
from app.schemas.document import DocumentResponse

# Enums
class OrderStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"

# Order Item Schemas
class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)

class OrderItemUpdate(BaseModel):
    """Schema for updating a single order item"""
    product_id: UUID
    quantity: int = Field(gt=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    unit_price: Optional[float] = Field(None, ge=0)

class OrderItemSingleUpdate(BaseModel):
    """Schema for updating a single order item via direct endpoint (product_id implied)"""
    product_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, gt=0)
    discount_percent: Optional[float] = Field(None, ge=0, le=100)
    unit_price: Optional[float] = Field(None, ge=0)

class OrderItemsUpdateRequest(BaseModel):
    """Schema for bulk updating order items"""
    items: List[OrderItemUpdate]

class OrderAcceptRequest(BaseModel):
    """Schema for accepting an order"""
    notes: Optional[str] = None

class OrderRejectRequest(BaseModel):
    """Schema for rejecting an order"""
    reason: str = Field(..., min_length=1)
    notes: Optional[str] = None

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
    product: Optional[ProductPublicResponse] = None

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
    documents: List['DocumentResponse'] = []
    client: Optional[ClientResponse] = None
    
    # Devis tracking
    devis_count: int = 0
    latest_devis: Optional['DocumentResponse'] = None

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