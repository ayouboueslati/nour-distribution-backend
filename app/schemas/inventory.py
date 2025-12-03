from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class MovementType(str, Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    RESERVED = "reserved"
    RELEASED = "released"

class InventoryMovementBase(BaseModel):
    movement_type: MovementType
    quantity: int = Field(..., ge=1)
    reason: str = Field(..., max_length=255)
    notes: Optional[str] = None
    reference_type: Optional[str] = Field(None, max_length=100)
    reference_id: Optional[UUID] = None

class InventoryMovementCreate(InventoryMovementBase):
    product_id: UUID

class InventoryMovementResponse(InventoryMovementBase):
    id: UUID
    product_id: UUID
    previous_stock: int
    new_stock: int
    performed_by: Optional[UUID]
    created_at: datetime
    
    # Nested product info
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class InventoryMovementListResponse(BaseModel):
    movements: List[InventoryMovementResponse]
    total: int

# Stock level response
class StockLevelResponse(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    reserved_quantity: int
    available_quantity: int
    min_stock_level: int
    max_stock_level: Optional[int]
    needs_restock: bool
    last_movement: Optional[datetime]

class LowStockAlertResponse(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    current_stock: int
    min_stock_level: int
    needed_quantity: int
    urgency: str  # "low", "medium", "high"