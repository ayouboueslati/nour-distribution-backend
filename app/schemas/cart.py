from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# Cart Item Schemas
class CartItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")

class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")

class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    cart_id: UUID
    product_id: UUID
    quantity: int
    reserved_at: Optional[datetime] = None
    reservation_expires_at: Optional[datetime] = None
    created_at: datetime
    
    # Include product details
    product: Optional[dict] = None

# Cart Schemas
class CartCreate(BaseModel):
    # No client_id required for creation - strictly guest based initially
    pass

class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    guest_session_id: Optional[str] = None # Expose guest_session_id
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: List[CartItemResponse] = []
    
    # Computed fields
    total_items: Optional[int] = None

class CartSummary(BaseModel):
    total_items: int
    total_quantity: int
    has_out_of_stock: bool
    out_of_stock_items: List[dict] = []