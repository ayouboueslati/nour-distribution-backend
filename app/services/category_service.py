from operator import and_
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.base import BaseService

class CategoryService(BaseService[Category]):
    def __init__(self, db: Session):
        super().__init__(Category, db)

    def create_category(self, category_data: CategoryCreate) -> Category:
        """Create a new category with validation"""
        # Check if slug already exists
        existing_category = self.db.query(Category).filter(
            Category.slug == category_data.slug
        ).first()

        if existing_category:
            # ✅ FIX: RAISE the error instead of returning it
            raise ValueError(f"category with slug '{category_data.slug}' already exists")
        
        return self.create(category_data.model_dump())  # ✅ Also changed .dict() to .model_dump()
    
    def update_category(self, category_id: UUID, category_data: CategoryUpdate) -> Optional[Category]:
        """Update category with validation"""
        category = self.get_by_id(category_id)
        if not category:
            return None

        update_data = category_data.model_dump(exclude_unset=True)  # ✅ Changed .dict() to .model_dump()
        
        # Check slug uniqueness if being updated
        if 'slug' in update_data and update_data['slug'] != category.slug:
            existing_category = self.db.query(Category).filter(
                and_(
                    Category.slug == update_data['slug'],
                    Category.id != category_id
                )
            ).first()
            if existing_category:
                raise ValueError(f"Category with slug '{update_data['slug']}' already exists")

        return self.update(category, update_data)

    def get_category_tree(self) -> List[Category]:
        """Get all categories with their subcategories"""
        return self.db.query(Category).filter(Category.parent_id == None).all()

    def get_subcategories(self, parent_id: UUID) -> List[Category]:
        """Get all subcategories of a parent category"""
        return self.db.query(Category).filter(Category.parent_id == parent_id).all()

    def get_categories_with_product_count(self) -> List[Category]:
        """Get categories with product counts"""
        from sqlalchemy import func
        from app.models.product import Product
        
        return self.db.query(
            Category,
            func.count(Product.id).label('products_count')
        ).outerjoin(Product).group_by(Category.id).all()

    def get_active_categories(self) -> List[Category]:
        """Get only active categories"""
        return self.db.query(Category).filter(Category.is_active == True).all()

    def get_featured_categories(self) -> List[Category]:
        """Get featured categories for homepage"""
        return self.db.query(Category).filter(
            and_(
                Category.is_active == True,
                Category.is_featured == True
            )
        ).all()