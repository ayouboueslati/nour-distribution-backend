from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID

class ProductImageBase(BaseModel):
    image_url: str = Field(..., max_length=500)
    alt_text: Optional[str] = Field(None, max_length=255)
    sort_order: int = Field(0, ge=0)
    is_primary: bool = False

class ProductImageCreate(ProductImageBase):
    product_id: UUID

class ProductImageUpdate(BaseModel):
    alt_text: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = Field(None, ge=0)
    is_primary: Optional[bool] = None

class ProductImageResponse(ProductImageBase):
    id: UUID
    product_id: UUID
    
    model_config = ConfigDict(from_attributes=True)