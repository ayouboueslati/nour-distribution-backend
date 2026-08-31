from pydantic_settings import BaseSettings, SettingsConfigDict
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
    
    # Email Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@nour-distribution.com"
    EMAIL_ENABLED: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.167.1:3000",
        "https://nour-distribution.vercel.app",
        "https://nour-distribution-git-main-ayoub-oueslatis-projects.vercel.app",
        "https://nour-distribution-5y3gg2ah8-ayoub-oueslatis-projects.vercel.app",
    ]
    
    
    # First Admin (for seeding)
    FIRST_SUPER_ADMIN_EMAIL: str
    FIRST_SUPER_ADMIN_PASSWORD: str
    FIRST_SUPER_ADMIN_NAME: str = "Super Admin"
    
    # Internal API Key (for microservices)
    INTERNAL_API_KEY: str = secrets.token_urlsafe(32)

    # Tunisian Specific
    TVA_RATE: float = 0.19  # Tunisian VAT is 19%
    TIMBRE_FISCAL_RATE: float = 1.000  # Stamp duty updated to 1.000 DT as per request
    PATENTE_REQUIRED: bool = True
    
    # Tunisian Bank Info
    BANK_NAME: str = "ATTIJARI BANK – MEGRINE"
    BANK_IBAN: str = "04072157007133053401"
    BANK_SWIFT: str = "" # Not provided
    
    # Tunisian Company Info
    COMPANY_NAME: str = "NOUR DISTRIBUTION"
    COMPANY_ACTIVITY: str = "ACCESSOIRES DE COIFFURE"
    COMPANY_ADDRESS: str = "87 Avenue de la République, 2033 Megrine – BEN AROUS"
    COMPANY_PHONE: str = "71 432 831"
    COMPANY_GSM: str = "98 224 294"
    COMPANY_EMAIL: str = "kamounassad@gmail.com"
    COMPANY_MATRICULE_FISCAL: str = "155546 / F"
    COMPANY_REGISTRE_COMMERCE: str = "B0244792018"
    COMPANY_RIB: str = "04072157007133053401"
    COMPANY_BANK: str = "ATTIJARI BANK – MEGRINE"
    COMPANY_CUSTOMS_CODE: str = "XXXXXXXXX"
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
    
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

settings = Settings()