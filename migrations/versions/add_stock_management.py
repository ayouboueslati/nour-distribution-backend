"""Add stock alerts and admin notifications tables

Revision ID: add_stock_management
Revises: 
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_stock_management'
down_revision = '85d955444897'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create stock_alerts table
    op.create_table(
        'stock_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.Enum('LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCK', 'EXPIRING_RESERVATION', 'STOCK_DISCREPANCY', name='alerttype'), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='alertpriority'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('threshold_value', sa.Integer(), nullable=True),
        sa.Column('current_value', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stock_alerts_product', 'stock_alerts', ['product_id'])
    op.create_index('idx_stock_alerts_active', 'stock_alerts', ['is_active'])
    op.create_index('idx_stock_alerts_priority', 'stock_alerts', ['priority'])
    op.create_index('idx_stock_alerts_type', 'stock_alerts', ['alert_type'])

    # Create admin_notifications table
    op.create_table(
        'admin_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.Enum('STOCK_MOVEMENT', 'STOCK_ALERT', 'ORDER_STATUS', 'LOW_STOCK', 'OUT_OF_STOCK', 'AVOIR_CREATED', 'FACTURE_CREATED', 'DEVIS_CREATED', name='notificationtype'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='notificationpriority'), nullable=False),
        sa.Column('target_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('related_entity_type', sa.String(length=50), nullable=True),
        sa.Column('related_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_by', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_admin_notifications_type', 'admin_notifications', ['notification_type'])
    op.create_index('idx_admin_notifications_priority', 'admin_notifications', ['priority'])
    op.create_index('idx_admin_notifications_created', 'admin_notifications', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_admin_notifications_read', 'admin_notifications', ['is_read'])


def downgrade():
    # Drop admin_notifications table
    op.drop_index('idx_admin_notifications_read', table_name='admin_notifications')
    op.drop_index('idx_admin_notifications_created', table_name='admin_notifications')
    op.drop_index('idx_admin_notifications_priority', table_name='admin_notifications')
    op.drop_index('idx_admin_notifications_type', table_name='admin_notifications')
    op.drop_table('admin_notifications')
    op.execute('DROP TYPE notificationtype')
    op.execute('DROP TYPE notificationpriority')

    # Drop stock_alerts table
    op.drop_index('idx_stock_alerts_type', table_name='stock_alerts')
    op.drop_index('idx_stock_alerts_priority', table_name='stock_alerts')
    op.drop_index('idx_stock_alerts_active', table_name='stock_alerts')
    op.drop_index('idx_stock_alerts_product', table_name='stock_alerts')
    op.drop_table('stock_alerts')
    op.execute('DROP TYPE alerttype')
    op.execute('DROP TYPE alertpriority')
