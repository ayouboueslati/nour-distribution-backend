import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import create_engine, text
from app.core.config import settings

def test_db():
    print(f"Connecting to: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL.replace("postgres://", "postgresql://"))
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print(f"Tables in public schema: {tables}")
        
        if 'suppliers' in tables:
            result = conn.execute(text("SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name = 'suppliers'"))
            columns = [f"{row[0]} (default: {row[1]}, nullable: {row[2]})" for row in result]
            print(f"\nColumns in 'suppliers':")
            for col in columns:
                print(f"  - {col}")

if __name__ == "__main__":
    test_db()
