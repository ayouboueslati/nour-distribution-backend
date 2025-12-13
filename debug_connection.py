
import sys
import os
import socket
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text # Import text

# Add current path to sys.path
sys.path.append(os.getcwd())

def check_port(host, port):
    print(f"Checking {host}:{port}...", end=" ")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        print("OPEN")
        s.close()
        return True
    except Exception as e:
        print(f"CLOSED/BLOCKED ({e})")
        return False

def check_db():
    print("Checking Database Connection...")
    try:
        from app.core.config import settings
        print(f"  DB URL defined: {bool(settings.DATABASE_URL)}")
        # Mask password for printing
        masked_url = settings.DATABASE_URL
        if ":" in masked_url and "@" in masked_url:
            print("  (URL contains credentials)")
        
        print(f"  Connecting to DB engine...", end=" ")
        engine = create_engine(settings.DATABASE_URL)
        connection = engine.connect()
        print("CONNECTED")
        
        print("  Running test query...", end=" ")
        connection.execute(text("SELECT 1")) # Use text() for the query
        print("SUCCESS")
        connection.close()
        return True
    except Exception as e:
        print(f"\n  DB ERROR: {e}")
        return False

if __name__ == "__main__":
    print(f"--- Debugging {time.ctime()} ---")
    
    # 1. Check Port 8000
    check_port("127.0.0.1", 8000)
    
    # 2. Check Database
    check_db()
    
    print("Done.")
