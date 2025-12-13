
import sys
import os
from sqlalchemy import create_mock_engine
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.models.document import Document, DocumentType, DocumentStatus

def dump(sql, *multiparams, **params):
    print(sql.compile(dialect=engine.dialect))

engine = create_mock_engine("postgresql://", dump)

def test_insert():
    print("Testing INSERT SQL generation...")
    doc = Document(
        id=uuid4(),
        type=DocumentType.DEVIS,
        document_number="TEST-001",
        status=DocumentStatus.EN_ATTENTE,
        client_id=uuid4(),
        issue_date=datetime.now()
    )
    
    # We seemingly need to trigger the compile
    # This involves some hacking because create_mock_engine is for DDL mostly or basic textual
    # Let's just use the models directly to see column definition
    
    print(f"Column 'status' values_callable: {Document.status.type.values_callable}")
    
    # Check if we can verify what it would persist
    # If values_callable is set, it should be working.
    
    # Let's try to mock the enum handling
    if Document.status.type.values_callable:
        print("values_callable is SET")
        values = Document.status.type.values_callable([DocumentStatus.EN_ATTENTE])
        print(f"Processed value for EN_ATTENTE: {values}")
    else:
        print("values_callable is NOT SET")

if __name__ == "__main__":
    test_insert()
