import sys
import os
from sqlalchemy.orm import Session

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings

def seed_first_admin(db: Session):
    """Create or update first super admin user"""
    # Check if admin exists
    existing_admin = db.query(User).filter(User.email == settings.FIRST_SUPER_ADMIN_EMAIL).first()
    
    password_hash = get_password_hash(settings.FIRST_SUPER_ADMIN_PASSWORD)
    
    if existing_admin:
        print(f"🔄 Updating existing admin: {existing_admin.email}")
        existing_admin.hashed_password = password_hash
        existing_admin.full_name = settings.FIRST_SUPER_ADMIN_NAME
        existing_admin.role = UserRole.SUPER_ADMIN
        existing_admin.is_active = True
    else:
        print(f"🆕 Creating new admin: {settings.FIRST_SUPER_ADMIN_EMAIL}")
        admin = User(
            email=settings.FIRST_SUPER_ADMIN_EMAIL,
            hashed_password=password_hash,
            full_name=settings.FIRST_SUPER_ADMIN_NAME,
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        db.add(admin)
    
    db.commit()
    print(f"✅ Admin user ready: {settings.FIRST_SUPER_ADMIN_EMAIL}")
    print(f"🔑 Password set to: {settings.FIRST_SUPER_ADMIN_PASSWORD}")

def seed_database():
    """Seed database with initial data"""
    db = SessionLocal()
    try:
        seed_first_admin(db)
        print("🎉 Database seeding completed successfully!")
    except Exception as e:
        print(f"❌ Database seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()