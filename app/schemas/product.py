from pydantic import BaseModel, ConfigDict, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    # Basic Information
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    
    # Identifiers
    sku: str = Field(..., min_length=1, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    
    # Categorization
    category_id: UUID
    
    # Hair-Specific Attributes
    hair_type: Optional[str] = Field(None, max_length=100)
    hair_texture: Optional[str] = Field(None, max_length=100)
    hair_length: Optional[str] = Field(None, max_length=50)
    hair_color: Optional[str] = Field(None, max_length=100)
    hair_origin: Optional[str] = Field(None, max_length=100)
    hair_quality: Optional[str] = Field(None, max_length=100)
    
    # Packaging
    weight_grams: Optional[int] = Field(None, ge=0)
    bundle_pieces: int = Field(1, ge=1)
    package_dimensions: Optional[str] = Field(None, max_length=100)
    
    # Inventory
    stock_quantity: int = Field(0, ge=0)
    min_stock_level: int = Field(5, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    
    # Supplier
    supplier_id: UUID
    supplier_sku: Optional[str] = Field(None, max_length=100)
    
    # Status & Visibility
    is_active: bool = True
    is_featured: bool = False
    is_best_seller: bool = False
    is_new_arrival: bool = True
    
    # Media
    main_image: Optional[str] = Field(None, max_length=500)
    
    # SEO
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    search_keywords: Optional[str] = None

class ProductCreate(ProductBase):
    # Pricing (admin only)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    wholesale_price: Optional[Decimal] = Field(None, ge=0)
    retail_price: Optional[Decimal] = Field(None, ge=0)
    
    @validator('max_stock_level')
    def validate_max_stock(cls, v, values):
        if v is not None and 'min_stock_level' in values:
            if v < values['min_stock_level']:
                raise ValueError('Max stock level must be greater than min stock level')
        return v

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    category_id: Optional[UUID] = None
    
    # Hair attributes
    hair_type: Optional[str] = Field(None, max_length=100)
    hair_texture: Optional[str] = Field(None, max_length=100)
    hair_length: Optional[str] = Field(None, max_length=50)
    hair_color: Optional[str] = Field(None, max_length=100)
    hair_origin: Optional[str] = Field(None, max_length=100)
    hair_quality: Optional[str] = Field(None, max_length=100)
    
    # Packaging
    weight_grams: Optional[int] = Field(None, ge=0)
    bundle_pieces: Optional[int] = Field(None, ge=1)
    package_dimensions: Optional[str] = Field(None, max_length=100)
    
    # Inventory
    stock_quantity: Optional[int] = Field(None, ge=0)
    min_stock_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    
    # Supplier
    supplier_id: Optional[UUID] = None
    supplier_sku: Optional[str] = Field(None, max_length=100)
    
    # Status
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_best_seller: Optional[bool] = None
    is_new_arrival: Optional[bool] = None
    
    # Media
    main_image: Optional[str] = Field(None, max_length=500)
    
    # SEO
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = None
    search_keywords: Optional[str] = None
    
    # Pricing (admin only)
    cost_price: Optional[Decimal] = Field(None, ge=0)
    wholesale_price: Optional[Decimal] = Field(None, ge=0)
    retail_price: Optional[Decimal] = Field(None, ge=0)

# Public response (no pricing)
class ProductPublicResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    short_description: Optional[str]
    sku: str
    category_id: UUID
    
    # Hair attributes
    hair_type: Optional[str]
    hair_texture: Optional[str]
    hair_length: Optional[str]
    hair_color: Optional[str]
    hair_origin: Optional[str]
    hair_quality: Optional[str]
    
    # Packaging
    weight_grams: Optional[int]
    bundle_pieces: int
    package_dimensions: Optional[str]
    
    # Inventory (only availability info)
    available_quantity: int
    needs_restock: bool
    
    # Status & Media
    is_active: bool
    is_featured: bool
    is_best_seller: bool
    is_new_arrival: bool
    main_image: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Relationships (nested)
    category: Optional["CategoryNestedResponse"] = None
    supplier: Optional["SupplierNestedResponse"] = None
    
    model_config = ConfigDict(from_attributes=True)

# Admin response (with pricing)
class ProductAdminResponse(ProductPublicResponse):
    # Pricing (admin only)
    cost_price: Optional[Decimal]
    wholesale_price: Optional[Decimal]
    retail_price: Optional[Decimal]
    
    # Full inventory info
    stock_quantity: int
    reserved_quantity: int
    min_stock_level: int
    max_stock_level: Optional[int]
    
    # Supplier info
    supplier_sku: Optional[str]

class ProductListResponse(BaseModel):
    products: List[ProductPublicResponse]
    total: int
    page: int
    page_size: int

class ProductAdminListResponse(BaseModel):
    products: List[ProductAdminResponse]
    total: int
    page: int
    page_size: int

# Stock update schema
class StockUpdate(BaseModel):
    quantity: int = Field(..., ge=0)
    reason: str = Field(..., max_length=255)
    notes: Optional[str] = None

# Import from other schemas
from app.schemas.category import CategoryNestedResponse
from app.schemas.supplier import SupplierNestedResponse

# Rebuild models to resolve forward references
ProductPublicResponse.model_rebuild()
ProductAdminResponse.model_rebuild()