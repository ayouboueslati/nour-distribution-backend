from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime

# Base schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=255, description="URL-friendly slug")
    parent_id: Optional[Union[UUID, str]] = None
    image_url: Optional[str] = None
    sort_order: int = Field(0, ge=0)
    is_active: bool = True
    is_featured: bool = False

# Create schema
class CategoryCreate(CategoryBase):
    pass

# Update schema
class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[UUID] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

# Response schemas
class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    subcategories: List["CategoryResponse"] = []
    products_count: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# For nested relationships
class CategoryNestedResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# List response
class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse]
    total: int

# Update forward reference
CategoryResponse.model_rebuild()