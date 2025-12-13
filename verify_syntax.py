
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Checking document_service.py...")
    from app.services.document_service import DocumentService
    print("document_service.py OK")
except Exception as e:
    print(f"document_service.py FAILED: {e}")

try:
    print("Checking order_service.py...")
    from app.services.order_service import OrderService
    print("order_service.py OK")
except Exception as e:
    print(f"order_service.py FAILED: {e}")
