from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import require_admin, require_manager
from app.models.user import User
from app.models.admin_notification import NotificationType, NotificationPriority
from app.services.admin_notification_service import AdminNotificationService
from pydantic import BaseModel

router = APIRouter()


# Schemas
class NotificationResponse(BaseModel):
    id: UUID
    notification_type: str
    title: str
    message: str
    priority: str
    target_roles: List[str]
    related_entity_type: Optional[str]
    related_entity_id: Optional[UUID]
    is_read: bool
    read_by: List[str]
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get notifications for current user based on their role - Admin+ only
    """
    notification_service = AdminNotificationService(db)
    
    try:
        notifications = notification_service.get_notifications_for_user(
            user=current_user,
            unread_only=unread_only,
            skip=skip,
            limit=limit
        )
        
        return {
            "notifications": notifications,
            "total": len(notifications),
            "page": skip // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving notifications: {str(e)}"
        )


@router.get("/notifications/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get count of unread notifications for current user - Admin+ only
    """
    notification_service = AdminNotificationService(db)
    
    try:
        count = notification_service.get_unread_count(current_user)
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting unread count: {str(e)}"
        )


@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Mark a notification as read - Admin+ only
    """
    notification_service = AdminNotificationService(db)
    
    try:
        notification = notification_service.mark_as_read(notification_id, current_user.id)
        return {"message": "Notification marked as read", "notification": notification}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking notification as read: {str(e)}"
        )


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Mark all notifications as read for current user - Admin+ only
    """
    notification_service = AdminNotificationService(db)
    
    try:
        count = notification_service.mark_all_as_read(current_user)
        return {"message": f"{count} notifications marked as read", "count": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking all notifications as read: {str(e)}"
        )


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a notification - Admin+ only
    """
    notification_service = AdminNotificationService(db)
    
    try:
        notification = notification_service.get_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification_service.delete(notification_id)
        return {"message": "Notification deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting notification: {str(e)}"
        )
