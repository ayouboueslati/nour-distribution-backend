import pytest
from datetime import datetime
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.core.database import get_db
from app.models.base import Base
# Import all models to ensure they are registered with Base
from app.models.user import User, UserRole
from app.models.product import Product
from app.models.client import Client
from app.models.order import Order, OrderItem, OrderHistory
from app.models.document import Document, DocumentItem, DocumentHistory, Payment
from app.models.inventory import InventoryMovement
from app.models.charge import Charge
from app.models.category import Category
from app.core.security import get_password_hash

# Use a file-based SQLite for more reliability in tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_avoir.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db) -> Generator:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db) -> User:
    user = User(
        email="test@user.com",
        hashed_password=get_password_hash("password"),
        full_name="Test User",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        failed_login_attempts=0,
        password_changed_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    return user
