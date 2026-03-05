import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.user_service import UserService
from app.core.config import settings
from app.models.user import UserRole, User

def create_super_admin():
    db: Session = SessionLocal()
    try:
        user_service = UserService(db)
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == settings.FIRST_SUPER_ADMIN_EMAIL).first()
        if existing_user:
            print(f"Super admin with email {settings.FIRST_SUPER_ADMIN_EMAIL} already exists.")
            return

        print(f"Creating super admin: {settings.FIRST_SUPER_ADMIN_NAME} ({settings.FIRST_SUPER_ADMIN_EMAIL})...")
        
        # We manually create the super admin to bypass any staff-level restrictions in the service
        from app.core.security import get_password_hash
        import uuid
        
        new_admin = User(
            id=uuid.uuid4(),
            email=settings.FIRST_SUPER_ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.FIRST_SUPER_ADMIN_PASSWORD),
            full_name=settings.FIRST_SUPER_ADMIN_NAME,
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print("Successfully created super admin!")
        
    except Exception as e:
        print(f"Error creating super admin: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
