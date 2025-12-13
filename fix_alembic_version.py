"""
Fix Alembic Version - Manual Database Update

The database has a stale revision '2b9d9f1eeb83' that doesn't exist in migration files.
This script updates the alembic_version table to the correct revision.
"""

import psycopg2
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    exit(1)

# Parse database URL
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path[1:]
)

cursor = conn.cursor()

print("Current alembic_version:")
cursor.execute("SELECT * FROM alembic_version")
current = cursor.fetchall()
print(current)

# Update to the latest migration revision
latest_revision = '932c0c3bc376'
print(f"\nUpdating to revision: {latest_revision}")

cursor.execute("UPDATE alembic_version SET version_num = %s", (latest_revision,))
conn.commit()

print("Updated alembic_version:")
cursor.execute("SELECT * FROM alembic_version")
updated = cursor.fetchall()
print(updated)

cursor.close()
conn.close()

print("\n✅ Database revision fixed! You can now run:")
print("alembic revision --autogenerate -m 'Add guest_session_id to carts'")
print("alembic upgrade head")
