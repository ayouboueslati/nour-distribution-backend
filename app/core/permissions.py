from typing import Optional, List
from app.models.user import User, UserRole
from enum import Enum


class Permission(str, Enum):
    """
    Define all possible permissions 
    """
    # User Management
    VIEW_USERS = "view_users"
    CREATE_USERS = "create_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"
    MANAGE_ADMINS = "manage_admins"
    RESET_PASSWORDS = "reset_passwords"
    DEACTIVATE_USERS = "deactivate_users"
    
    # Product Management
    VIEW_PRODUCTS = "view_products"
    CREATE_PRODUCTS = "create_products"
    EDIT_PRODUCTS = "edit_products"
    DELETE_PRODUCTS = "delete_products"
    IMPORT_PRODUCTS = "import_products"
    EXPORT_PRODUCTS = "export_products"
    
    # Category Management
    VIEW_CATEGORIES = "view_categories"
    MANAGE_CATEGORIES = "manage_categories"
    
    # Inventory Management
    VIEW_INVENTORY = "view_inventory"
    MANAGE_INVENTORY = "manage_inventory"
    ADJUST_STOCK = "adjust_stock"
    VIEW_INVENTORY_MOVEMENTS = "view_inventory_movements"
    
    # Supplier Management
    VIEW_SUPPLIERS = "view_suppliers"
    CREATE_SUPPLIERS = "create_suppliers"
    EDIT_SUPPLIERS = "edit_suppliers"
    DELETE_SUPPLIERS = "delete_suppliers"
    
    # Order Management
    VIEW_ORDERS = "view_orders"
    CREATE_ORDERS = "create_orders"
    EDIT_ORDERS = "edit_orders"
    DELETE_ORDERS = "delete_orders"
    CANCEL_ORDERS = "cancel_orders"
    
    # Client Management
    VIEW_CLIENTS = "view_clients"
    MANAGE_CLIENTS = "manage_clients"
    
    # Analytics & Reports
    VIEW_ANALYTICS = "view_analytics"
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    VIEW_FINANCIAL_DATA = "view_financial_data"
    
    # System Settings
    VIEW_SETTINGS = "view_settings"
    EDIT_SETTINGS = "edit_settings"
    MANAGE_SYSTEM = "manage_system"


# ============================================================================
# ROLE PERMISSION MAPPING
# Define what each role can do
# ============================================================================

ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    # ========================================================================
    # SUPER ADMIN - Full system access, can do everything
    # ========================================================================
    UserRole.SUPER_ADMIN: [
        # All permissions - Super Admin is God Mode
        *list(Permission),
    ],
    
    # ========================================================================
    # ADMIN - Full operational access, cannot manage super admins
    # ========================================================================
    UserRole.ADMIN: [
        # User Management
        Permission.VIEW_USERS,
        Permission.CREATE_USERS,
        Permission.EDIT_USERS,
        Permission.DELETE_USERS,
        Permission.RESET_PASSWORDS,
        Permission.DEACTIVATE_USERS,
        # Note: Cannot manage other admins or super admins
        
        # Product Management - Full Access
        Permission.VIEW_PRODUCTS,
        Permission.CREATE_PRODUCTS,
        Permission.EDIT_PRODUCTS,
        Permission.DELETE_PRODUCTS,
        Permission.IMPORT_PRODUCTS,
        Permission.EXPORT_PRODUCTS,
        
        # Category Management - Full Access
        Permission.VIEW_CATEGORIES,
        Permission.MANAGE_CATEGORIES,
        
        # Inventory Management - Full Access
        Permission.VIEW_INVENTORY,
        Permission.MANAGE_INVENTORY,
        Permission.ADJUST_STOCK,
        Permission.VIEW_INVENTORY_MOVEMENTS,
        
        # Supplier Management - Full Access
        Permission.VIEW_SUPPLIERS,
        Permission.CREATE_SUPPLIERS,
        Permission.EDIT_SUPPLIERS,
        Permission.DELETE_SUPPLIERS,
        
        # Order Management - Full Access
        Permission.VIEW_ORDERS,
        Permission.CREATE_ORDERS,
        Permission.EDIT_ORDERS,
        Permission.DELETE_ORDERS,
        Permission.CANCEL_ORDERS,
        
        # Client Management - Full Access
        Permission.VIEW_CLIENTS,
        Permission.MANAGE_CLIENTS,
        
        # Analytics & Reports - Full Access
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_FINANCIAL_DATA,
        
        # Settings - View Only
        Permission.VIEW_SETTINGS,
        # Note: Cannot edit system settings
    ],
    
    # ========================================================================
    # MANAGER - Operational management, no user or system management
    # ========================================================================
    UserRole.MANAGER: [
        # User Management - View Only
        Permission.VIEW_USERS,
        
        # Product Management - Full Access
        Permission.VIEW_PRODUCTS,
        Permission.CREATE_PRODUCTS,
        Permission.EDIT_PRODUCTS,
        Permission.EXPORT_PRODUCTS,
        # Note: Cannot delete products
        
        # Category Management - View Only
        Permission.VIEW_CATEGORIES,
        
        # Inventory Management - Full Access
        Permission.VIEW_INVENTORY,
        Permission.MANAGE_INVENTORY,
        Permission.ADJUST_STOCK,
        Permission.VIEW_INVENTORY_MOVEMENTS,
        
        # Supplier Management - View and Create
        Permission.VIEW_SUPPLIERS,
        Permission.CREATE_SUPPLIERS,
        # Note: Cannot edit or delete suppliers
        
        # Order Management - Full Access
        Permission.VIEW_ORDERS,
        Permission.CREATE_ORDERS,
        Permission.EDIT_ORDERS,
        Permission.CANCEL_ORDERS,
        # Note: Cannot delete orders
        
        # Client Management - Full Access
        Permission.VIEW_CLIENTS,
        Permission.MANAGE_CLIENTS,
        
        # Analytics & Reports - View Access
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_REPORTS,
        # Note: Cannot export reports or view financial data
    ],
    
    # ========================================================================
    # STAFF - Basic operational access, read-mostly
    # ========================================================================
    UserRole.STAFF: [
        # Product Management - View Only
        Permission.VIEW_PRODUCTS,
        
        # Category Management - View Only
        Permission.VIEW_CATEGORIES,
        
        # Inventory Management - View Only
        Permission.VIEW_INVENTORY,
        Permission.VIEW_INVENTORY_MOVEMENTS,
        
        # Supplier Management - View Only
        Permission.VIEW_SUPPLIERS,
        
        # Order Management - View and Create
        Permission.VIEW_ORDERS,
        Permission.CREATE_ORDERS,
        
        # Client Management - View Only
        Permission.VIEW_CLIENTS,
        
        # No Analytics or Settings Access
    ],
}


# ============================================================================
# ROLE HIERARCHY
# Higher number = more power
# ============================================================================

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.SUPER_ADMIN: 100,
    UserRole.ADMIN: 80,
    UserRole.MANAGER: 60,
    UserRole.STAFF: 40,
}


# ============================================================================
# PERMISSION SERVICE
# Main class for all permission checks
# ============================================================================

class PermissionService:
    """
    Centralized permission checking service
    All permission checks should go through this service
    """
    
    # ========================================================================
    # BASIC PERMISSION CHECKS
    # ========================================================================
    
    @staticmethod
    def has_permission(user: User, permission: Permission) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user: The user to check
            permission: The permission to verify
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        if not user or not user.is_active:
            return False
        
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions
    
    @staticmethod
    def has_any_permission(user: User, permissions: List[Permission]) -> bool:
        """Check if user has ANY of the specified permissions"""
        if not user or not user.is_active:
            return False
        
        return any(PermissionService.has_permission(user, perm) for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user: User, permissions: List[Permission]) -> bool:
        """Check if user has ALL of the specified permissions"""
        if not user or not user.is_active:
            return False
        
        return all(PermissionService.has_permission(user, perm) for perm in permissions)
    
    @staticmethod
    def get_user_permissions(user: User) -> List[Permission]:
        """Get all permissions for a user"""
        if not user or not user.is_active:
            return []
        
        return ROLE_PERMISSIONS.get(user.role, [])
    
    # ========================================================================
    # ROLE HIERARCHY CHECKS
    # ========================================================================
    
    @staticmethod
    def get_role_level(role: UserRole) -> int:
        """Get the hierarchical level of a role"""
        return ROLE_HIERARCHY.get(role, 0)
    
    @staticmethod
    def is_higher_role(user_role: UserRole, target_role: UserRole) -> bool:
        """Check if user_role is higher than target_role in hierarchy"""
        return ROLE_HIERARCHY.get(user_role, 0) > ROLE_HIERARCHY.get(target_role, 0)
    
    @staticmethod
    def is_same_or_higher_role(user_role: UserRole, target_role: UserRole) -> bool:
        """Check if user_role is same or higher than target_role"""
        return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(target_role, 0)
    
    # ========================================================================
    # USER MANAGEMENT PERMISSIONS
    # ========================================================================
    
    @staticmethod
    def can_manage_users(current_user: User, target_user: Optional[User] = None) -> bool:
        """
        Check if current user can manage users
        
        Rules:
        - Must have VIEW_USERS permission
        - Can only manage users with lower role
        - Super admin can manage everyone
        - Admin cannot manage admins or super admins
        """
        if not current_user or not current_user.is_active:
            return False
        
        # Must have basic permission
        if not PermissionService.has_permission(current_user, Permission.VIEW_USERS):
            return False
        
        # If no specific target, check general permission
        if target_user is None:
            return True
        
        # Cannot manage yourself for certain actions
        if current_user.id == target_user.id:
            return False
        
        # Check role hierarchy
        return PermissionService.is_higher_role(current_user.role, target_user.role)
    
    @staticmethod
    def can_delete_user(current_user: User, target_user: User) -> bool:
        """
        Check if user can permanently delete another user
        
        Rules:
        - Must have DELETE_USERS permission
        - Cannot delete yourself
        - Can only delete users with lower role
        """
        if not current_user or not current_user.is_active:
            return False
        
        # Cannot delete yourself
        if current_user.id == target_user.id:
            return False
        
        # Must have permission
        if not PermissionService.has_permission(current_user, Permission.DELETE_USERS):
            return False
        
        # Check role hierarchy
        return PermissionService.is_higher_role(current_user.role, target_user.role)
    
    @staticmethod
    def can_change_role(current_user: User, new_role: UserRole) -> bool:
        """
        Check if user can assign a specific role
        
        Rules:
        - Super admin can assign any role
        - Admin can assign manager and staff only
        - Others cannot assign roles
        """
        if not current_user or not current_user.is_active:
            return False
        
        # Super admin can assign any role
        if current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Admin can assign roles below admin
        if current_user.role == UserRole.ADMIN:
            return new_role in [UserRole.MANAGER, UserRole.STAFF]
        
        return False
    
    @staticmethod
    def can_reset_password(current_user: User, target_user: User) -> bool:
        """
        Check if user can reset another user's password
        
        Rules:
        - Must have RESET_PASSWORDS permission
        - Can only reset passwords of users with lower role
        """
        if not current_user or not current_user.is_active:
            return False
        
        # Must have permission
        if not PermissionService.has_permission(current_user, Permission.RESET_PASSWORDS):
            return False
        
        # Check role hierarchy
        return PermissionService.is_higher_role(current_user.role, target_user.role)
    
    # ========================================================================
    # QUICK ROLE CHECKS
    # ========================================================================
    
    @staticmethod
    def is_super_admin(user: User) -> bool:
        """Check if user is super admin"""
        return user.role == UserRole.SUPER_ADMIN if user else False
    
    @staticmethod
    def is_admin_or_higher(user: User) -> bool:
        """Check if user is admin or super admin"""
        return user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN] if user else False
    
    @staticmethod
    def is_manager_or_higher(user: User) -> bool:
        """Check if user is manager or above"""
        return user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER] if user else False
    
    # ========================================================================
    # RESOURCE-SPECIFIC PERMISSIONS
    # ========================================================================
    
    @staticmethod
    def can_delete_product(user: User) -> bool:
        """Only admin and super admin can delete products"""
        return PermissionService.has_permission(user, Permission.DELETE_PRODUCTS)
    
    @staticmethod
    def can_manage_inventory(user: User) -> bool:
        """Manager and above can manage inventory"""
        return PermissionService.has_permission(user, Permission.MANAGE_INVENTORY)
    
    @staticmethod
    def can_manage_suppliers(user: User) -> bool:
        """Check if user can fully manage suppliers"""
        return PermissionService.has_all_permissions(user, [
            Permission.CREATE_SUPPLIERS,
            Permission.EDIT_SUPPLIERS,
            Permission.DELETE_SUPPLIERS
        ])
    
    @staticmethod
    def can_view_financial_data(user: User) -> bool:
        """Only admin and super admin can view financial data"""
        return PermissionService.has_permission(user, Permission.VIEW_FINANCIAL_DATA)
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    @staticmethod
    def get_permission_error_message(permission: Permission) -> str:
        """Get user-friendly error message for missing permission"""
        messages = {
            Permission.VIEW_USERS: "Vous n'avez pas la permission de voir les utilisateurs",
            Permission.CREATE_USERS: "Vous n'avez pas la permission de créer des utilisateurs",
            Permission.EDIT_USERS: "Vous n'avez pas la permission de modifier les utilisateurs",
            Permission.DELETE_USERS: "Vous n'avez pas la permission de supprimer les utilisateurs",
            Permission.MANAGE_ADMINS: "Seul le Super Admin peut gérer les administrateurs",
            Permission.DELETE_PRODUCTS: "Seuls les administrateurs peuvent supprimer des produits",
            Permission.MANAGE_INVENTORY: "Vous n'avez pas la permission de gérer les stocks",
            Permission.VIEW_FINANCIAL_DATA: "Vous n'avez pas accès aux données financières",
            Permission.EDIT_SETTINGS: "Seul le Super Admin peut modifier les paramètres système",
        }
        return messages.get(permission, "Permission refusée")
    
    @staticmethod
    def get_accessible_roles(user: User) -> List[UserRole]:
        """Get list of roles that user can assign to others"""
        if not user or not user.is_active:
            return []
        
        if user.role == UserRole.SUPER_ADMIN:
            return list(UserRole)
        
        if user.role == UserRole.ADMIN:
            return [UserRole.MANAGER, UserRole.STAFF]
        
        return []