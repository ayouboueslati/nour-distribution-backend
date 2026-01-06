from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, or_

from app.models.admin_notification import AdminNotification, NotificationType, NotificationPriority
from app.models.user import User, UserRole
from app.services.base import BaseService
from app.services.notification_service import NotificationService


class AdminNotificationService(BaseService[AdminNotification]):
    def __init__(self, db: Session):
        super().__init__(AdminNotification, db)
        self.email_service = NotificationService()
    
    def create_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority,
        target_roles: List[str],
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        send_email: bool = False
    ) -> AdminNotification:
        """Create a new admin notification."""
        notification = AdminNotification(
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            target_roles=target_roles,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            created_by=created_by,
            is_read=False,
            read_by=[]
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Send email for critical notifications
        if send_email and priority == NotificationPriority.CRITICAL:
            self._send_email_to_admins(notification, target_roles)
        
        return notification
    
    def _send_email_to_admins(self, notification: AdminNotification, target_roles: List[str]) -> None:
        """Send email notification to admins with target roles."""
        try:
            # Get users with target roles
            users = self.db.query(User).filter(
                and_(
                    User.is_active == True,
                    User.role.in_(target_roles)
                )
            ).all()
            
            for user in users:
                try:
                    self.email_service.send_email(
                        to_email=user.email,
                        subject=f"🚨 {notification.title}",
                        html_content=f"""
                        <h2>{notification.title}</h2>
                        <p><strong>Priority:</strong> {notification.priority.value.upper()}</p>
                        <p>{notification.message}</p>
                        <p><small>This is an automated notification from the stock management system.</small></p>
                        """,
                        text_content=f"{notification.title}\n\n{notification.message}"
                    )
                except Exception as e:
                    print(f"Failed to send email to {user.email}: {e}")
        except Exception as e:
            print(f"Error sending email notifications: {e}")
    
    def get_notifications_for_user(
        self,
        user: User,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> List[AdminNotification]:
        """Get notifications for a user based on their role."""
        query = self.db.query(AdminNotification).filter(
            AdminNotification.target_roles.contains([user.role.value])
        )
        
        if unread_only:
            # Check if user ID is not in read_by array
            query = query.filter(
                or_(
                    ~AdminNotification.read_by.contains([str(user.id)]),
                    AdminNotification.read_by == []
                )
            )
        
        return query.order_by(desc(AdminNotification.created_at)).offset(skip).limit(limit).all()
    
    def get_unread_count(self, user: User) -> int:
        """Get count of unread notifications for a user."""
        return self.db.query(AdminNotification).filter(
            and_(
                AdminNotification.target_roles.contains([user.role.value]),
                or_(
                    ~AdminNotification.read_by.contains([str(user.id)]),
                    AdminNotification.read_by == []
                )
            )
        ).count()
    
    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> AdminNotification:
        """Mark a notification as read by a specific user."""
        notification = self.get_by_id(notification_id)
        if not notification:
            raise ValueError("Notification not found")
        
        # Add user ID to read_by array if not already there
        read_by_list = notification.read_by or []
        user_id_str = str(user_id)
        
        if user_id_str not in read_by_list:
            read_by_list.append(user_id_str)
            notification.read_by = read_by_list
            notification.read_at = datetime.now(timezone.utc)
            notification.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(notification)
        
        return notification
    
    def mark_all_as_read(self, user: User) -> int:
        """Mark all notifications as read for a user. Returns count of marked notifications."""
        notifications = self.get_notifications_for_user(user, unread_only=True, limit=1000)
        
        count = 0
        for notification in notifications:
            self.mark_as_read(notification.id, user.id)
            count += 1
        
        return count
    
    # Helper methods for specific notification types
    
    def notify_stock_movement(
        self,
        product_name: str,
        movement_type: str,
        quantity: int,
        product_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AdminNotification:
        """Create notification for stock movement."""
        return self.create_notification(
            notification_type=NotificationType.STOCK_MOVEMENT,
            title=f"Stock Movement: {product_name}",
            message=f"{movement_type.upper()}: {quantity} units of '{product_name}'",
            priority=NotificationPriority.LOW,
            target_roles=[UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="product",
            related_entity_id=product_id,
            created_by=user_id
        )
    
    def notify_low_stock(
        self,
        product_name: str,
        current_stock: int,
        min_stock: int,
        product_id: UUID
    ) -> AdminNotification:
        """Create notification for low stock."""
        priority = NotificationPriority.CRITICAL if current_stock == 0 else NotificationPriority.HIGH
        notification_type = NotificationType.OUT_OF_STOCK if current_stock == 0 else NotificationType.LOW_STOCK
        
        return self.create_notification(
            notification_type=notification_type,
            title=f"{'Out of Stock' if current_stock == 0 else 'Low Stock'}: {product_name}",
            message=f"Product '{product_name}' has {current_stock} units (minimum: {min_stock}). {'URGENT: Restock immediately!' if current_stock == 0 else 'Please restock soon.'}",
            priority=priority,
            target_roles=[UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="product",
            related_entity_id=product_id,
            send_email=(current_stock == 0)  # Send email for out of stock
        )
    
    def notify_avoir_created(
        self,
        avoir_number: str,
        facture_number: str,
        total_amount: float,
        returned_items_count: int,
        avoir_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AdminNotification:
        """Create notification for avoir creation."""
        return self.create_notification(
            notification_type=NotificationType.AVOIR_CREATED,
            title=f"Avoir Created: {avoir_number}",
            message=f"Avoir {avoir_number} created for facture {facture_number}. Amount: {total_amount} DT. {returned_items_count} item(s) returned to stock.",
            priority=NotificationPriority.MEDIUM,
            target_roles=[UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="document",
            related_entity_id=avoir_id,
            created_by=user_id
        )
    
    def notify_order_status_change(
        self,
        order_number: str,
        old_status: str,
        new_status: str,
        order_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AdminNotification:
        """Create notification for order status change."""
        return self.create_notification(
            notification_type=NotificationType.ORDER_STATUS,
            title=f"Order Status Changed: {order_number}",
            message=f"Order {order_number} status changed from {old_status} to {new_status}",
            priority=NotificationPriority.LOW,
            target_roles=[UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="order",
            related_entity_id=order_id,
            created_by=user_id
        )
    
    def notify_facture_created(
        self,
        facture_number: str,
        devis_number: str,
        total_amount: float,
        facture_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AdminNotification:
        """Create notification for facture creation."""
        return self.create_notification(
            notification_type=NotificationType.FACTURE_CREATED,
            title=f"Facture Created: {facture_number}",
            message=f"Facture {facture_number} created from devis {devis_number}. Total: {total_amount} DT. Stock has been deducted.",
            priority=NotificationPriority.MEDIUM,
            target_roles=[UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="document",
            related_entity_id=facture_id,
            created_by=user_id
        )
    
    def notify_devis_created(
        self,
        devis_number: str,
        order_number: str,
        total_amount: float,
        devis_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AdminNotification:
        """Create notification for devis creation."""
        return self.create_notification(
            notification_type=NotificationType.DEVIS_CREATED,
            title=f"Devis Created: {devis_number}",
            message=f"Devis {devis_number} created for order {order_number}. Total: {total_amount} DT.",
            priority=NotificationPriority.LOW,
            target_roles=[UserRole.MANAGER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value],
            related_entity_type="document",
            related_entity_id=devis_id,
            created_by=user_id
        )
