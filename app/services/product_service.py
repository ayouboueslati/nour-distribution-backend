from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.product import Product
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.inventory import InventoryMovement, MovementType
from app.schemas.product import ProductCreate, ProductUpdate, StockUpdate
from app.services.base import BaseService

class ProductService(BaseService[Product]):
    def __init__(self, db: Session):
        super().__init__(Product, db)

    def create_product(self, product_data: ProductCreate) -> Product:
        """Create a new product with validation"""
        # Check if SKU already exists
        existing_product = self.db.query(Product).filter(
            Product.sku == product_data.sku
        ).first()
        
        if existing_product:
            raise ValueError(f"Product with SKU '{product_data.sku}' already exists")

        # Check if barcode is unique if provided
        if product_data.barcode:
            existing_barcode = self.db.query(Product).filter(
                Product.barcode == product_data.barcode
            ).first()
            if existing_barcode:
                raise ValueError(f"Product with barcode '{product_data.barcode}' already exists")

        # Verify category exists
        category = self.db.query(Category).filter(Category.id == product_data.category_id).first()
        if not category:
            raise ValueError("Category not found")

        # Verify supplier exists
        supplier = self.db.query(Supplier).filter(Supplier.id == product_data.supplier_id).first()
        if not supplier:
            raise ValueError("Supplier not found")

        product_dict = product_data.model_dump()
        product = self.create(product_dict)

        # Create initial inventory movement for stock
        if product_data.stock_quantity > 0:
            self._create_inventory_movement(
                product.id,
                MovementType.STOCK_IN,
                product_data.stock_quantity,
                0,
                product_data.stock_quantity,
                "initial_stock",
                "Initial stock creation"
            )

        return product

    def update_product(self, product_id: UUID, product_data: ProductUpdate) -> Optional[Product]:
        """Update product with validation and inventory tracking"""
        product = self.get_by_id(product_id)
        if not product:
            return None

        update_data = product_data.model_dump(exclude_unset=True)

        # Handle stock quantity changes
        if 'stock_quantity' in update_data and update_data['stock_quantity'] != product.stock_quantity:
            quantity_diff = update_data['stock_quantity'] - product.stock_quantity
            movement_type = MovementType.STOCK_IN if quantity_diff > 0 else MovementType.STOCK_OUT
            
            self._create_inventory_movement(
                product_id,
                movement_type,
                abs(quantity_diff),
                product.stock_quantity,
                update_data['stock_quantity'],
                "manual_adjustment",
                "Manual stock adjustment"
            )

        # Validate unique constraints
        if 'sku' in update_data and update_data['sku'] != product.sku:
            existing_sku = self.db.query(Product).filter(
                and_(
                    Product.sku == update_data['sku'],
                    Product.id != product_id
                )
            ).first()
            if existing_sku:
                raise ValueError(f"Product with SKU '{update_data['sku']}' already exists")

        if 'barcode' in update_data and update_data['barcode'] != product.barcode:
            existing_barcode = self.db.query(Product).filter(
                and_(
                    Product.barcode == update_data['barcode'],
                    Product.id != product_id
                )
            ).first()
            if existing_barcode:
                raise ValueError(f"Product with barcode '{update_data['barcode']}' already exists")

        return self.update(product, update_data)

    def delete_product(self, product_id: UUID) -> bool :
        """Delete a product and handle related inventory movements"""
        product = self.get_by_id(product_id)
        if not product:
            return False

        try:
            #first, delete all related inventory movements
            self.db.query(InventoryMovement).filter(
                InventoryMovement.product_id == product_id
            ).delete()

            #then, delete the product itself
            self.db.delete(product)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e    

    
    def get_product_with_details(self, product_id: UUID) -> Optional[Product]:
        """Get product with category and supplier details"""
        return self.db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.supplier),
            joinedload(Product.images)
        ).filter(Product.id == product_id).first()

    def get_products_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[UUID] = None,
        supplier_id: Optional[UUID] = None,
        hair_type: Optional[str] = None,
        hair_length: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None
    ) -> List[Product]:
        """Get products with advanced filtering"""
        query = self.db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.supplier)
        )

        # Apply filters
        if category_id:
            query = query.filter(Product.category_id == category_id)
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        if hair_type:
            query = query.filter(Product.hair_type == hair_type)
        if hair_length:
            query = query.filter(Product.hair_length == hair_length)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        if search_term:
            search_filter = or_(
                Product.name.ilike(f"%{search_term}%"),
                Product.sku.ilike(f"%{search_term}%"),
                Product.description.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)

        return query.offset(skip).limit(limit).all()

    def update_stock(
        self,
        product_id: UUID,
        stock_data: StockUpdate,
        user_id: Optional[UUID] = None
    ) -> Optional[Product]:
        """Update product stock with inventory tracking"""
        product = self.get_by_id(product_id)
        if not product:
            return None

        previous_stock = product.stock_quantity
        product.stock_quantity = stock_data.quantity
        
        # Create inventory movement
        movement_type = (
            MovementType.STOCK_IN if stock_data.quantity > previous_stock 
            else MovementType.STOCK_OUT
        )
        
        self._create_inventory_movement(
            product_id,
            movement_type,
            abs(stock_data.quantity - previous_stock),
            previous_stock,
            stock_data.quantity,
            stock_data.reason,
            stock_data.notes,
            user_id
        )

        self.db.commit()
        self.db.refresh(product)
        return product

    def get_low_stock_products(self) -> List[Product]:
        """Get products that need restocking"""
        return self.db.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.stock_quantity <= Product.min_stock_level
            )
        ).all()

    def get_products_by_supplier(self, supplier_id: UUID) -> List[Product]:
        """Get all products from a specific supplier"""
        return self.db.query(Product).filter(Product.supplier_id == supplier_id).all()

    def get_featured_products(self) -> List[Product]:
        """Get featured products for homepage"""
        return self.db.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.is_featured == True,
                Product.stock_quantity > 0
            )
        ).all()

    def get_best_sellers(self) -> List[Product]:
        """Get best-selling products"""
        # This would typically join with order items to calculate best sellers
        # For now, return products marked as best sellers
        return self.db.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.is_best_seller == True,
                Product.stock_quantity > 0
            )
        ).all()

    def _create_inventory_movement(
        self,
        product_id: UUID,
        movement_type: MovementType,
        quantity: int,
        previous_stock: int,
        new_stock: int,
        reason: str,
        notes: Optional[str] = None,
        user_id: Optional[UUID] = None
    ):
        """Helper method to create inventory movement records"""
        movement = InventoryMovement(
            product_id=product_id,
            movement_type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=reason,
            notes=notes,
            performed_by=user_id
        )
        self.db.add(movement)
        self.db.commit()