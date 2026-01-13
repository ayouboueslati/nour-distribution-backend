import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password, get_password_hash

def test_admin_user():
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@nourdistribution.com").first()
        
        if admin:
            print(f"✅ Admin user found: {admin.email}")
            print(f"📝 Full name: {admin.full_name}")
            print(f"🎯 Role: {admin.role}")
            print(f"🔓 Active: {admin.is_active}")
            
            # Test password - use environment variable or default for testing
            test_password = os.getenv("TEST_ADMIN_PASSWORD", "ChangeThisPassword123!")  # nosec B105
            is_correct = verify_password(test_password, admin.hashed_password)
            print(f"🔑 Password verification: {is_correct}")
            
            if not is_correct:
                print("❌ Password doesn't match!")
                print(f"💡 Current hash: {admin.hashed_password}")
                new_hash = get_password_hash(test_password)
                print(f"💡 Expected hash: {new_hash}")
        else:
            print("❌ No admin user found!")
            
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_admin_user()