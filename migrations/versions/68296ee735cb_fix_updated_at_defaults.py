"""fix_updated_at_defaults

Revision ID: 68296ee735cb
Revises: 4b206a3ea4d0
Create Date: 2026-03-07 04:44:05.680035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68296ee735cb'
down_revision: Union[str, None] = '4b206a3ea4d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # List of tables that need the updated_at default fix
    tables = [
        'users', 'carts', 'cart_items', 'order_history', 'documents', 
        'order_items', 'orders', 'charges', 'products', 'suppliers',
        'categories', 'inventory_movements', 'product_images'
    ]
    
    for table in tables:
        op.alter_column(table, 'updated_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=sa.text('now()'),
                   existing_nullable=False)


def downgrade() -> None:
    tables = [
        'users', 'carts', 'cart_items', 'order_history', 'documents', 
        'order_items', 'orders', 'charges', 'products', 'suppliers',
        'categories', 'inventory_movements', 'product_images'
    ]
    
    for table in tables:
        op.alter_column(table, 'updated_at',
                   existing_type=sa.DateTime(timezone=True),
                   server_default=None,
                   existing_nullable=False)
