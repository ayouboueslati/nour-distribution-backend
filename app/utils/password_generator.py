import secrets
import string
import re
from typing import Dict

class PasswordGenerator:
    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """
        Generate a secure random password with:
        - Uppercase letters
        - Lowercase letters
        - Digits
        - Special characters
        """
        if length <8:
            raise ValueError('Password length must be at least 8 characters')
        
        # Character Set
        uppercase =  string.ascii_uppercase
        lowercase =  string.ascii_lowercase
        digits    =  string.digits
        special   =  "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Ensure at least one character from each set
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Fill the rest with  random choices from all sets
        all_char = uppercase + lowercase + digits + special
        password.extend(secrets.choice(all_char) for _ in range(length - 4))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, bool]:
         """
        Validate password strength and return detailed feedback
        """
         return{
             "length": len(password)>= 8,
             "uppecase": bool(re.search(r'[A-Z]', password)),
             "lowercase": bool(re.search(r'[a-z]', password)),
             "digit": bool(re.search(r'\d', password)),
             "special": bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password)),
              "secure": len(password) >= 12 and all([
                  bool(re.search(r'[A-Z]', password)),
                  bool(re.search(r'[a-z]', password)),
                  bool(re.search(r'\d', password)),
                  bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))
              ])     
         }
    
    @staticmethod
    def generate_user_credentials() -> Dict[str, str]:
        """Generate secure credentials for new users"""
        password = PasswordGenerator.generate_secure_password()
        return {
            "password": password,
            "strength": PasswordGenerator.validate_password_strength(password)
        }