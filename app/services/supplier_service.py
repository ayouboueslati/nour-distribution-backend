from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.supplier import Supplier
from app.models.product import Product
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.base import BaseService

class SupplierService(BaseService[Supplier]):
    def __init__(self, db: Session):
        super().__init__(Supplier, db)

    def create_supplier(self, supplier_data: SupplierCreate) -> Supplier:
        """Create a new supplier with validation"""
        # Check if company name already exists
        existing_supplier = self.db.query(Supplier).filter(
            func.lower(Supplier.company_name) == func.lower(supplier_data.company_name)
        ).first()
        
        if existing_supplier:
            raise ValueError(f"Supplier with company name '{supplier_data.company_name}' already exists")

        return self.create(supplier_data.dict())

    def update_supplier(self, supplier_id: UUID, supplier_data: SupplierUpdate) -> Optional[Supplier]:
        """Update supplier with validation"""
        supplier = self.get_by_id(supplier_id)
        if not supplier:
            return None

        update_data = supplier_data.dict(exclude_unset=True)
        
        # Check company name uniqueness if being updated
        if 'company_name' in update_data:
            existing_supplier = self.db.query(Supplier).filter(
                and_(
                    func.lower(Supplier.company_name) == func.lower(update_data['company_name']),
                    Supplier.id != supplier_id
                )
            ).first()
            if existing_supplier:
                raise ValueError(f"Supplier with company name '{update_data['company_name']}' already exists")

        return self.update(supplier, update_data)

    def get_suppliers_with_stats(self) -> List[Dict[str, Any]]:
        """Get suppliers with product counts and performance stats"""
        suppliers_with_stats = self.db.query(
            Supplier,
            func.count(Product.id).label('products_count'),
            func.avg(Product.cost_price).label('avg_product_cost')
        ).outerjoin(Product).group_by(Supplier.id).all()

        result = []
        for supplier, products_count, avg_product_cost in suppliers_with_stats:
            result.append({
                'supplier': supplier,
                'products_count': products_count,
                'avg_product_cost': float(avg_product_cost) if avg_product_cost else 0.0
            })

        return result

    def get_preferred_suppliers(self) -> List[Supplier]:
        """Get preferred suppliers"""
        return self.db.query(Supplier).filter(
            and_(
                Supplier.is_active == True,
                Supplier.is_preferred == True
            )
        ).all()

    def get_supplier_performance_metrics(self, supplier_id: UUID) -> Dict[str, Any]:
        """Get detailed performance metrics for a supplier"""
        supplier = self.get_by_id(supplier_id)
        if not supplier:
            raise ValueError("Supplier not found")

        # Get product stats
        product_stats = self.db.query(
            func.count(Product.id).label('total_products'),
            func.sum(Product.stock_quantity).label('total_stock'),
            func.avg(Product.cost_price).label('avg_cost')
        ).filter(Product.supplier_id == supplier_id).first()

        return {
            'supplier': supplier,
            'total_products': product_stats.total_products or 0,
            'total_stock_value': (product_stats.total_stock or 0) * (product_stats.avg_cost or 0),
            'average_product_cost': float(product_stats.avg_cost or 0),
            'performance_rating': {
                'reliability': supplier.reliability_rating,
                'quality': supplier.quality_rating,
                'communication': supplier.communication_rating,
                'overall': (supplier.reliability_rating + supplier.quality_rating + supplier.communication_rating) / 3
            }
        }