import json
from sqlalchemy import create_engine, text
from app.core.config import settings

def dump_schema():
    engine = create_engine(settings.DATABASE_URL.replace("postgres://", "postgresql://"))
    schema_info = {}
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        schema_info["tables"] = tables
        
        schema_info["columns"] = {}
        for table in tables:
            result = conn.execute(text(f"SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name = '{table}'"))
            schema_info["columns"][table] = [{"name": row[0], "default": row[1], "nullable": row[2]} for row in result]
            
    with open("schema_dump.json", "w") as f:
        json.dump(schema_info, f, indent=2)

if __name__ == "__main__":
    dump_schema()
