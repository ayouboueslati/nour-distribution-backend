from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from typing import List

class PermissionService:
    @staticmethod
    def can_manage_users(current_user: User, target_user: User = None) -> bool:
        """
        Check if current user can manage users
        - Super admin can manage everyone
        - Admin can manage managers and staff
        - Managers can only view
        - Staff cannot manage users
        """
        if current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if current_user.role == UserRole.ADMIN:
            if target_user:
                return target_user.role in [UserRole.MANAGER, UserRole.STAFF]
            return True
        
        return False
    
    @staticmethod
    def can_delete_user(current_user: User, target_user: User) -> bool:
        """Check if user can delete another user"""
        if current_user.id == target_user.id:
            return False  # Cannot delete yourself
        
        if current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if current_user.role == UserRole.ADMIN:
            return target_user.role in [UserRole.MANAGER, UserRole.STAFF]
        
        return False
    
    @staticmethod
    def can_change_role(current_user: User, new_role: UserRole) -> bool:
        """Check if user can assign a specific role"""
        if current_user.role == UserRole.SUPER_ADMIN:
            return True
        
        if current_user.role == UserRole.ADMIN:
            return new_role in [UserRole.MANAGER, UserRole.STAFF]
        
        return False

