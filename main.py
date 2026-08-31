from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from datetime import datetime
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",  # Explicitly set docs URL
    redoc_url="/redoc" # Explicitly set redoc URL
)

from fastapi.staticfiles import StaticFiles
import os

# Create static directory if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware — origins come from settings.CORS_ORIGINS (includes localhost:3000 + production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow(),
        "docs_available": True
    }

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=f"{settings.PROJECT_NAME} API Documentation",
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    # Use environment variable for host, default to 0.0.0.0 for development
    # In production, override with more specific host via environment variable
    uvicorn.run(
        "main:app", 
        host=os.getenv("HOST", "0.0.0.0"),  # nosec B104 - configurable via environment
        port=int(os.getenv("PORT", "8000")), 
        reload=True,
        log_level="debug"  # Add debug logging
    )
