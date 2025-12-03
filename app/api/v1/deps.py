from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Callable
from app.core.database import get_db
from app.core.security import verify_token
from app.core.permissions import Permission, PermissionService
from app.models.user import User, UserRole
from app.services.user_service import UserService

security = HTTPBearer()


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    Raises 401 if token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user_service = UserService(db)
    user = user_service.get_user_by_email(email)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# ============================================================================
# PERMISSION-BASED DEPENDENCIES
# ============================================================================

def require_permission(permission: Permission):
    """
    Create a dependency that requires a specific permission
    
    Usage:
        @router.get("/products")
        async def get_products(
            current_user: User = Depends(require_permission(Permission.VIEW_PRODUCTS))
        ):
            ...
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not PermissionService.has_permission(current_user, permission):
            error_message = PermissionService.get_permission_error_message(permission)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message
            )
        return current_user
    
    return permission_checker


def require_any_permission(*permissions: Permission):
    """
    Create a dependency that requires ANY of the specified permissions
    
    Usage:
        @router.get("/analytics")
        async def get_analytics(
            current_user: User = Depends(
                require_any_permission(Permission.VIEW_ANALYTICS, Permission.VIEW_REPORTS)
            )
        ):
            ...
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not PermissionService.has_any_permission(current_user, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez avoir l'une des permissions suivantes: {', '.join([p.value for p in permissions])}"
            )
        return current_user
    
    return permission_checker


def require_all_permissions(*permissions: Permission):
    """
    Create a dependency that requires ALL of the specified permissions
    
    Usage:
        @router.delete("/products/{id}")
        async def delete_product(
            current_user: User = Depends(
                require_all_permissions(Permission.VIEW_PRODUCTS, Permission.DELETE_PRODUCTS)
            )
        ):
            ...
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not PermissionService.has_all_permissions(current_user, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez avoir toutes ces permissions: {', '.join([p.value for p in permissions])}"
            )
        return current_user
    
    return permission_checker


# ============================================================================
# ROLE-BASED DEPENDENCIES (Backward Compatibility)
# ============================================================================

def require_role(*required_roles: UserRole):
    """
    Role-based access control dependency
    
    Usage:
        @router.get("/admin/settings")
        async def get_settings(
            current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))
        ):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle insuffisant. Rôles requis: {', '.join([r.value for r in required_roles])}. Votre rôle: {current_user.role.value}",
            )
        return current_user
    return role_checker


# ============================================================================
# QUICK ROLE DEPENDENCIES
# ============================================================================

require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_admin = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN)
require_manager = require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)


# ============================================================================
# SPECIFIC PERMISSION DEPENDENCIES (Common Use Cases)
# ============================================================================

# User Management
require_user_view = require_permission(Permission.VIEW_USERS)
require_user_create = require_permission(Permission.CREATE_USERS)
require_user_edit = require_permission(Permission.EDIT_USERS)
require_user_delete = require_permission(Permission.DELETE_USERS)

# Product Management
require_product_view = require_permission(Permission.VIEW_PRODUCTS)
require_product_create = require_permission(Permission.CREATE_PRODUCTS)
require_product_edit = require_permission(Permission.EDIT_PRODUCTS)
require_product_delete = require_permission(Permission.DELETE_PRODUCTS)

# Inventory Management
require_inventory_view = require_permission(Permission.VIEW_INVENTORY)
require_inventory_manage = require_permission(Permission.MANAGE_INVENTORY)

# Supplier Management
require_supplier_view = require_permission(Permission.VIEW_SUPPLIERS)
require_supplier_manage = require_any_permission(
    Permission.CREATE_SUPPLIERS,
    Permission.EDIT_SUPPLIERS,
    Permission.DELETE_SUPPLIERS
)

# Order Management
require_order_view = require_permission(Permission.VIEW_ORDERS)
require_order_create = require_permission(Permission.CREATE_ORDERS)
require_order_edit = require_permission(Permission.EDIT_ORDERS)

# Analytics
require_analytics = require_permission(Permission.VIEW_ANALYTICS)
require_financial_data = require_permission(Permission.VIEW_FINANCIAL_DATA)

# Settings
require_settings_view = require_permission(Permission.VIEW_SETTINGS)
require_settings_edit = require_permission(Permission.EDIT_SETTINGS)


# ============================================================================
# HELPER FUNCTION FOR MANUAL CHECKS IN ENDPOINTS
# ============================================================================

def check_permission(user: User, permission: Permission) -> None:
    """
    Manually check permission and raise HTTPException if denied
    
    Usage in endpoint:
        check_permission(current_user, Permission.DELETE_PRODUCTS)
    """
    if not PermissionService.has_permission(user, permission):
        error_message = PermissionService.get_permission_error_message(permission)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message
        )


def check_user_management_permission(current_user: User, target_user: User) -> None:
    """
    Check if current user can manage target user
    
    Usage:
        check_user_management_permission(current_user, target_user)
    """
    if not PermissionService.can_manage_users(current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas gérer cet utilisateur. Rôle insuffisant."
        )