from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template, Environment, FileSystemLoader
import os
from app.core.config import settings

class NotificationService:
    """Email notification service for order status changes"""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.enabled = settings.EMAIL_ENABLED
        
        # Setup Jinja2 environment for templates
        # Using absolute path relative to the app directory for better reliability
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, '..', 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
    
    def _get_base_context(self):
        """Get base context for all email templates"""
        return {
            "current_year": datetime.now().year,
            "company_name": "NOUR DISTRIBUTION",
            "company_email": "contact@nour-distribution.tn",
            "company_phone": "+216 71 123 456",
            "company_address": "Rue Habib Bourguiba, Tunis 1001, Tunisie",
            "company_website": "https://www.nour-distribution.tn"
        }
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email"""
        if not to_email or "@" not in to_email:
            print(f"[EMAIL] Skip sending: Invalid or missing recipient email: '{to_email}'")
            return
            
        if not self.enabled or not self.smtp_username or not self.smtp_password:
            print(f"[EMAIL] Would send to {to_email}: {subject}")
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email
        
        # Add plain text content if provided
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        
        # Add HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"[EMAIL] Sent to {to_email}: {subject}")
            
        except Exception as e:
            print(f"[EMAIL ERROR] Type: {type(e).__name__}")
            print(f"[EMAIL ERROR] Details: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def notify_order_submitted(self, order: Dict, client_email: str, client_name: str):
        """Notify client that order was submitted"""
        try:
            template = self.jinja_env.get_template('emails/order_submitted.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "order_number": order["order_number"],
                "order_date": order["submitted_at"].strftime("%d/%m/%Y") if isinstance(order["submitted_at"], datetime) else order["submitted_at"],
                "items_count": len(order["items"]),
                "total_items": sum(item["quantity"] for item in order["items"]),
                "order_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/orders/{order['id']}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Confirmation de votre commande #{order['order_number']}",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_order_submitted: {e}")
    
    def notify_order_processed(self, order: Dict, client_email: str, client_name: str, admin_name: str):
        """Notify client that order is being processed with pricing"""
        try:
            template = self.jinja_env.get_template('emails/order_processed.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "order_number": order["order_number"],
                "processed_by": admin_name,
                "subtotal": float(order["subtotal"] or 0.0),
                "shipping_fee": float(order["shipping_fee"] or 0.0),
                "tax_amount": float(order["tax_amount"] or 0.0),
                "total_amount": float(order["total_amount"] or 0.0),
                "items": order["items"],
                "devis_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/documents/{order.get('latest_devis_id', '')}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Devis pour votre commande #{order['order_number']}",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_order_processed: {e}")
    
    def notify_order_confirmed(self, order: Dict, client_email: str, client_name: str):
        """Notify client that order was confirmed"""
        try:
            template = self.jinja_env.get_template('emails/order_confirmed.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "order_number": order["order_number"],
                "confirmed_date": order["confirmed_at"].strftime("%d/%m/%Y") if isinstance(order["confirmed_at"], datetime) else order["confirmed_at"],
                "total_amount": order["total_amount"],
                "order_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/orders/{order['id']}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Commande #{order['order_number']} confirmée",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_order_confirmed: {e}")
    
    def notify_devis_created(self, devis: Dict, client_email: str, client_name: str):
        """Notify client about new devis"""
        try:
            template = self.jinja_env.get_template('emails/devis_created.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "devis_number": devis["document_number"],
                "issue_date": devis["issue_date"].strftime("%d/%m/%Y") if isinstance(devis["issue_date"], datetime) else devis["issue_date"],
                "total_amount": devis["total_amount"],
                "due_date": devis["due_date"].strftime("%d/%m/%Y") if devis.get("due_date") and isinstance(devis["due_date"], datetime) else None,
                "devis_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/documents/{devis['id']}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Nouveau devis #{devis['document_number']}",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_devis_created: {e}")
    
    def notify_devis_accepted(self, devis: Dict, client_email: str, client_name: str):
        """Notify client that devis was accepted"""
        try:
            template = self.jinja_env.get_template('emails/devis_accepted.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "devis_number": devis["document_number"],
                "accepted_date": devis["accepted_date"].strftime("%d/%m/%Y") if isinstance(devis["accepted_date"], datetime) else devis["accepted_date"],
                "total_amount": devis["total_amount"],
                "due_date": devis["due_date"].strftime("%d/%m/%Y") if devis.get("due_date") and isinstance(devis["due_date"], datetime) else None,
                "facture_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/documents/{devis.get('related_facture_id', '')}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Devis #{devis['document_number']} accepté",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_devis_accepted: {e}")
    
    def notify_facture_created(self, facture: Dict, client_email: str, client_name: str):
        """Notify client about new facture"""
        try:
            # Check if template exists, if not use a simple HTML string
            try:
                template = self.jinja_env.get_template('emails/facture_created.html')
            except:
                # Fallback simple template
                template_str = """
                <!DOCTYPE html>
                <html>
                <body>
                    <h2>Nouvelle Facture</h2>
                    <p>Bonjour {{ client_name }},</p>
                    <p>Votre facture #{{ facture_number }} a été créée.</p>
                    <p>Montant: {{ total_amount }} DT</p>
                    <p>Cordialement,<br>{{ company_name }}</p>
                </body>
                </html>
                """
                template = Template(template_str)
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "facture_number": facture["document_number"],
                "issue_date": facture["issue_date"].strftime("%d/%m/%Y") if isinstance(facture["issue_date"], datetime) else facture["issue_date"],
                "total_amount": facture["total_amount"],
                "due_date": facture["due_date"].strftime("%d/%m/%Y") if facture.get("due_date") and isinstance(facture["due_date"], datetime) else None,
                "facture_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/documents/{facture['id']}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Nouvelle facture #{facture['document_number']}",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_facture_created: {e}")
    
    def notify_payment_received(self, payment: Dict, facture: Dict, client_email: str, client_name: str):
        """Notify client about payment received"""
        try:
            template = self.jinja_env.get_template('emails/payment_received.html')
            
            context = self._get_base_context()
            context.update({
                "client_name": client_name,
                "facture_number": facture["document_number"],
                "payment_amount": payment["amount"],
                "payment_method": payment["payment_method"],
                "payment_date": payment["payment_date"].strftime("%d/%m/%Y") if isinstance(payment["payment_date"], datetime) else payment["payment_date"],
                "remaining_amount": facture["remaining_amount"],
                "receipt_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/documents/{facture['id']}/payments/{payment['id']}"
            })
            
            html = template.render(context)
            
            self.send_email(
                to_email=client_email,
                subject=f"Paiement reçu pour facture #{facture['document_number']}",
                html_content=html
            )
        except Exception as e:
            print(f"[EMAIL ERROR] notify_payment_received: {e}")