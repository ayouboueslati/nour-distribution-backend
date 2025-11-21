from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, products, clients, orders, analytics
from app.api.v1.endpoints.admin import users as admin_users
from app.api.v1.endpoints.profile import users as profile_users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(profile_users.router, prefix="/profile", tags=["user-profile"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

