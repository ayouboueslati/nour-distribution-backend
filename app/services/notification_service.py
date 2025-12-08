from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os

class NotificationService:
    """Email notification service for order status changes"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@nour-distribution.com")
        
        # Email templates
        self.templates = {
            "order_submitted": self._load_template("order_submitted.html"),
            "order_processed": self._load_template("order_processed.html"),
            "order_confirmed": self._load_template("order_confirmed.html"),
            "devis_created": self._load_template("devis_created.html"),
            "devis_accepted": self._load_template("devis_accepted.html"),
            "facture_created": self._load_template("facture_created.html"),
            "payment_received": self._load_template("payment_received.html")
        }
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email with base context"""
         # Add base context to all templates
        from jinja2 import Template
    
        base_context = self._get_base_context()
    
        # If html_content is a template string, render it
        if isinstance(html_content, Template):
            html_content = html_content.render(**base_context)
        elif isinstance(html_content, str):
         # It's already rendered
            pass
    

    def _load_template(self, template_name: str) -> Template:
        """Load email template"""
        template_path = f"app/templates/emails/{template_name}"
        with open(template_path, 'r', encoding='utf-8') as f:
            return Template(f.read())
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """Send email"""
        if not self.smtp_username or not self.smtp_password:
            print(f"[EMAIL] Would send to {to_email}: {subject}")
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email
        
        # Add HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Add plain text content if provided
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"[EMAIL] Sent to {to_email}: {subject}")
            
        except Exception as e:
            print(f"[EMAIL] Failed to send: {e}")
    
    def notify_order_submitted(self, order: Dict, client_email: str, client_name: str):
        """Notify client that order was submitted"""
        html = self.templates["order_submitted"].render(
            client_name=client_name,
            order_number=order["order_number"],
            order_date=order["submitted_at"].strftime("%d/%m/%Y"),
            items_count=len(order["items"]),
            total_items=sum(item["quantity"] for item in order["items"]),
            order_url=f"{os.getenv('FRONTEND_URL')}/orders/{order['id']}"
        )
        
        self.send_email(
            to_email=client_email,
            subject=f"Confirmation de votre commande #{order['order_number']}",
            html_content=html
        )
    
    def notify_order_processed(self, order: Dict, client_email: str, client_name: str, admin_name: str):
        """Notify client that order is being processed with pricing"""
        html = self.templates["order_processed"].render(
            client_name=client_name,
            order_number=order["order_number"],
            processed_by=admin_name,
            subtotal=order["subtotal"],
            shipping_fee=order["shipping_fee"],
            tax_amount=order["tax_amount"],
            total_amount=order["total_amount"],
            items=order["items"],
            devis_url=f"{os.getenv('FRONTEND_URL')}/documents/{order['latest_devis_id']}"
        )
        
        self.send_email(
            to_email=client_email,
            subject=f"Devis pour votre commande #{order['order_number']}",
            html_content=html
        )
    
    def notify_devis_accepted(self, devis: Dict, client_email: str, client_name: str):
        """Notify client that devis was accepted"""
        html = self.templates["devis_accepted"].render(
            client_name=client_name,
            devis_number=devis["document_number"],
            accepted_date=devis["accepted_date"].strftime("%d/%m/%Y"),
            total_amount=devis["total_amount"],
            due_date=devis["due_date"].strftime("%d/%m/%Y") if devis["due_date"] else None,
            facture_url=f"{os.getenv('FRONTEND_URL')}/documents/{devis['related_facture_id']}"
        )
        
        self.send_email(
            to_email=client_email,
            subject=f"Devis #{devis['document_number']} accepté",
            html_content=html
        )
    
    def notify_payment_received(self, payment: Dict, facture: Dict, client_email: str, client_name: str):
        """Notify client about payment received"""
        html = self.templates["payment_received"].render(
            client_name=client_name,
            facture_number=facture["document_number"],
            payment_amount=payment["amount"],
            payment_method=payment["payment_method"],
            payment_date=payment["payment_date"].strftime("%d/%m/%Y"),
            remaining_amount=facture["remaining_amount"],
            receipt_url=f"{os.getenv('FRONTEND_URL')}/documents/{facture['id']}/payments/{payment['id']}"
        )
        
        self.send_email(
            to_email=client_email,
            subject=f"Paiement reçu pour facture #{facture['document_number']}",
            html_content=html
        )


        # Add this method to NotificationService class
def _get_base_context(self):
    """Get base context for all email templates"""
    from datetime import datetime
    return {
        "current_year": datetime.now().year,
        "company_name": "NOUR DISTRIBUTION",
        "company_email": "contact@nour-distribution.tn",
        "company_phone": "+216 71 123 456",
        "company_address": "Rue Habib Bourguiba, Tunis 1001, Tunisie"
    }

