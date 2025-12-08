from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, categories, suppliers, products, 
    inventory, clients, carts, orders, documents
)
from app.api.v1.endpoints.admin import users as admin_users
from app.api.v1.endpoints.profile import users as profile_users
from app.api.v1.endpoints import client_portal

api_router = APIRouter()

# Auth
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Users
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(profile_users.router, prefix="/profile", tags=["profile"])

# Products & Inventory
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])

# Client Management
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])

# Cart System
api_router.include_router(carts.router, prefix="/carts", tags=["carts"])

# Order Management (Commandes)
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

# Document Management (Devis, Factures, Avoirs)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

# Client Portal (for clients to view their orders/documents)
api_router.include_router(client_portal.router, prefix="/client-portal", tags=["client-portal"])