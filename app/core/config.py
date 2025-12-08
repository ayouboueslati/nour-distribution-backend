from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Nour Distribution"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000","http://192.168.167.1:3000"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # First Admin (for seeding)
    FIRST_SUPER_ADMIN_EMAIL: str
    FIRST_SUPER_ADMIN_PASSWORD: str
    FIRST_SUPER_ADMIN_NAME: str = "Super Admin"
    
    # Internal API Key (for microservices)
    INTERNAL_API_KEY: str = secrets.token_urlsafe(32)

    # Tunisian Specific
    TVA_RATE: float = 0.19  # Tunisian VAT is 19%
    TIMBRE_FISCAL_RATE: float = 0.005  # 0.5% stamp duty
    PATENTE_REQUIRED: bool = True
    
    # Tunisian Bank Info
    BANK_NAME: str = "Banque de Tunisie"  # Update with actual bank
    BANK_IBAN: str = "TN59 1234 5678 9012 3456 7890"
    BANK_SWIFT: str = "BKTUTNTT"
    
    # Tunisian Company Info
    COMPANY_MATRICULE_FISCAL: str = ""
    COMPANY_REGISTRE_COMMERCE: str = ""
    COMPANY_IDENTIFIANT_UNIQUE: str = ""
    
    # Tunisian Payment Methods
    ALLOWED_PAYMENT_METHODS: List[str] = [
        "especes", 
        "cheque", 
        "virement", 
        "carte", 
        "postal", 
        "mobile"
    ]
    
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()