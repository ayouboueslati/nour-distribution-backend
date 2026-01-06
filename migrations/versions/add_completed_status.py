"""add completed status to order

Revision ID: add_completed_status
Revises: add_stock_management
Create Date: 2026-01-05 15:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_completed_status'
down_revision = 'add_stock_management'
branch_labels = None
depends_on = None


def upgrade():
    # Add COMPLETED to the orderstatus enum
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'COMPLETED'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values easily
    # This is a no-op downgrade
    pass
