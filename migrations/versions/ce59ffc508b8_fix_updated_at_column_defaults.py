"""fix_updated_at_column_defaults

Revision ID: abc123  # Alembic generated this
Revises: 904ed82a6ae1  # Or None if first

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abc123'  # Keep what Alembic generated
down_revision = '904ed82a6ae1'  # ✅ Change to None if first migration, or actual ID

branch_labels = None
depends_on = None


def upgrade():
    """
    Add DEFAULT now() to updated_at columns for all tables
    """
    # Get database connection
    connection = op.get_bind()
    
    # Find all tables with updated_at column
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND column_name = 'updated_at'
        AND table_name NOT LIKE 'alembic_%'
    """))
    
    tables = [row[0] for row in result]
    
    print(f"\n📋 Found {len(tables)} tables with updated_at column")
    
    for table in tables:
        print(f"🔧 Fixing table: {table}")
        
        try:
            # Add DEFAULT
            connection.execute(sa.text(f"""
                ALTER TABLE {table} 
                ALTER COLUMN updated_at SET DEFAULT now()
            """))
            
            # Fix NULL values
            connection.execute(sa.text(f"""
                UPDATE {table} 
                SET updated_at = COALESCE(updated_at, created_at, now())
                WHERE updated_at IS NULL
            """))
            
            # Add NOT NULL constraint
            connection.execute(sa.text(f"""
                ALTER TABLE {table}
                ALTER COLUMN updated_at SET NOT NULL
            """))
            
            print(f"   ✅ Fixed: {table}")
            
        except Exception as e:
            print(f"   ⚠️ Error fixing {table}: {e}")
            # Don't fail entire migration if one table has issues
            continue


def downgrade():
    """
    Rollback changes (remove defaults)
    """
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND column_name = 'updated_at'
        AND table_name NOT LIKE 'alembic_%'
    """))
    
    tables = [row[0] for row in result]
    
    print(f"\n⏮️ Reverting {len(tables)} tables")
    
    for table in tables:
        try:
            connection.execute(sa.text(f"""
                ALTER TABLE {table}
                ALTER COLUMN updated_at DROP DEFAULT
            """))
            
            connection.execute(sa.text(f"""
                ALTER TABLE {table}
                ALTER COLUMN updated_at DROP NOT NULL
            """))
            
            print(f"   ⏮️ Reverted: {table}")
            
        except Exception as e:
            print(f"   ⚠️ Error reverting {table}: {e}")
            continue