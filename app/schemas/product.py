from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    sku: str
    stock_quantity: int = 0
    min_stock_level: int = 5

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True