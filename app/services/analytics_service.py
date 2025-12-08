from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case, and_, or_
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

class AnalyticsService:
    """Advanced analytics service for admin dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_analytics(self, period: str = "monthly") -> Dict:
        """Get sales analytics with Moroccan business metrics"""
        from app.models.document import Document, DocumentType, DocumentStatus
        from app.models.order import Order, OrderStatus
        
        end_date = datetime.utcnow()
        
        if period == "daily":
            start_date = end_date - timedelta(days=30)
            group_by = func.date(Document.issue_date)
        elif period == "weekly":
            start_date = end_date - timedelta(days=90)
            group_by = func.date_trunc('week', Document.issue_date)
        else:  # monthly
            start_date = end_date - timedelta(days=365)
            group_by = func.date_trunc('month', Document.issue_date)
        
        # Sales by period
        sales_query = self.db.query(
            group_by.label('period'),
            func.sum(Document.total_amount).label('total_sales'),
            func.count(Document.id).label('document_count'),
            func.avg(Document.total_amount).label('avg_sale')
        ).filter(
            Document.type == DocumentType.FACTURE,
            Document.status == DocumentStatus.PAYE,
            Document.issue_date.between(start_date, end_date)
        ).group_by(group_by).order_by('period')
        
        # Sales by client type
        from app.models.client import Client, ClientType
        
        sales_by_client_type = self.db.query(
            Client.type,
            func.sum(Document.total_amount).label('total_sales'),
            func.count(Document.id).label('facture_count')
        ).join(Document, Document.client_id == Client.id).filter(
            Document.type == DocumentType.FACTURE,
            Document.status == DocumentStatus.PAYE,
            Document.issue_date.between(start_date, end_date)
        ).group_by(Client.type)
        
        # Top products by revenue
        from app.models.document import DocumentItem
        
        top_products = self.db.query(
            DocumentItem.product_name,
            func.sum(DocumentItem.quantity).label('total_quantity'),
            func.sum(DocumentItem.subtotal).label('total_revenue'),
            func.avg(DocumentItem.unit_price).label('avg_price')
        ).join(Document, DocumentItem.document_id == Document.id).filter(
            Document.type == DocumentType.FACTURE,
            Document.status == DocumentStatus.PAYE,
            Document.issue_date.between(start_date, end_date)
        ).group_by(DocumentItem.product_name).order_by(func.sum(DocumentItem.subtotal).desc()).limit(10)
        
        # Payment collection efficiency
        payment_efficiency = self.db.query(
            func.avg(
                case(
                    [
                        (Document.paid_amount > 0, 
                         func.extract('day', Document.payments[0].payment_date - Document.issue_date))
                    ],
                    else_=0
                )
            ).label('avg_payment_days'),
            func.sum(
                case(
                    [
                        (Document.remaining_amount == 0, 1)
                    ],
                    else_=0
                )
            ).label('paid_factures'),
            func.count(Document.id).label('total_factures')
        ).filter(
            Document.type == DocumentType.FACTURE,
            Document.issue_date.between(start_date, end_date)
        ).first()
        
        # Moroccan VAT analytics
        vat_analytics = self.db.query(
            func.sum(Document.tax_amount).label('total_tva_collected'),
            func.avg(Document.tax_amount).label('avg_tva_per_facture'),
            func.max(Document.tax_amount).label('max_tva')
        ).filter(
            Document.type == DocumentType.FACTURE,
            Document.status == DocumentStatus.PAYE,
            Document.issue_date.between(start_date, end_date)
        ).first()
        
        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "sales_trend": [
                {
                    "period": row.period.strftime("%Y-%m-%d"),
                    "total_sales": float(row.total_sales or 0),
                    "document_count": row.document_count,
                    "avg_sale": float(row.avg_sale or 0)
                }
                for row in sales_query.all()
            ],
            "sales_by_client_type": [
                {
                    "client_type": row.type.value,
                    "total_sales": float(row.total_sales or 0),
                    "facture_count": row.facture_count
                }
                for row in sales_by_client_type.all()
            ],
            "top_products": [
                {
                    "product_name": row.product_name,
                    "total_quantity": row.total_quantity,
                    "total_revenue": float(row.total_revenue or 0),
                    "avg_price": float(row.avg_price or 0)
                }
                for row in top_products.all()
            ],
            "payment_efficiency": {
                "avg_payment_days": float(payment_efficiency.avg_payment_days or 0),
                "paid_factures": payment_efficiency.paid_factures,
                "total_factures": payment_efficiency.total_factures,
                "collection_rate": (payment_efficiency.paid_factures / payment_efficiency.total_factures * 100) 
                    if payment_efficiency.total_factures > 0 else 0
            },
            "vat_analytics": {
                "total_tva_collected": float(vat_analytics.total_tva_collected or 0),
                "avg_tva_per_facture": float(vat_analytics.avg_tva_per_facture or 0),
                "max_tva": float(vat_analytics.max_tva or 0)
            }
        }
    
    def get_stock_analytics(self) -> Dict:
        """Get comprehensive stock analytics"""
        from app.models.product import Product
        from app.models.inventory import InventoryMovement, MovementType
        
        # Stock levels overview
        stock_overview = self.db.query(
            func.count(Product.id).label('total_products'),
            func.sum(Product.stock_quantity).label('total_stock'),
            func.sum(Product.reserved_quantity).label('total_reserved'),
            func.sum(case([(Product.available_quantity <= 0, 1)], else_=0)).label('out_of_stock'),
            func.sum(case([(Product.available_quantity <= Product.min_stock_level, 1)], else_=0)).label('low_stock'),
            func.avg(Product.available_quantity).label('avg_stock_level')
        ).first()
        
        # Stock value by category
        from app.models.category import Category
        
        stock_value = self.db.query(
            Category.name,
            func.sum(Product.stock_quantity * Product.cost_price).label('stock_value'),
            func.count(Product.id).label('product_count'),
            func.avg(Product.available_quantity).label('avg_available')
        ).join(Product, Product.category_id == Category.id).group_by(Category.name).all()
        
        # Stock movements (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        movements = self.db.query(
            InventoryMovement.movement_type,
            func.sum(InventoryMovement.quantity).label('total_quantity'),
            func.count(InventoryMovement.id).label('movement_count')
        ).filter(
            InventoryMovement.created_at >= thirty_days_ago
        ).group_by(InventoryMovement.movement_type).all()
        
        # Slow moving items
        slow_moving = self.db.query(
            Product.name,
            Product.sku,
            Product.available_quantity,
            Product.min_stock_level,
            func.coalesce(
                self.db.query(func.sum(InventoryMovement.quantity))
                .filter(
                    InventoryMovement.product_id == Product.id,
                    InventoryMovement.movement_type == MovementType.STOCK_OUT,
                    InventoryMovement.created_at >= thirty_days_ago
                ).scalar_subquery(), 0
            ).label('sales_last_30_days')
        ).filter(
            Product.is_active == True
        ).having(
            func.coalesce(
                self.db.query(func.sum(InventoryMovement.quantity))
                .filter(
                    InventoryMovement.product_id == Product.id,
                    InventoryMovement.movement_type == MovementType.STOCK_OUT,
                    InventoryMovement.created_at >= thirty_days_ago
                ).scalar_subquery(), 0
            ) < 5  # Less than 5 sales in 30 days
        ).all()
        
        # Stock turnover ratio
        stock_turnover = self.db.query(
            func.avg(
                case([
                    (Product.cost_price > 0, 
                     func.coalesce(
                         self.db.query(func.sum(InventoryMovement.quantity))
                         .filter(
                             InventoryMovement.product_id == Product.id,
                             InventoryMovement.movement_type == MovementType.STOCK_OUT,
                             InventoryMovement.created_at >= thirty_days_ago
                         ).scalar_subquery(), 0
                     ) / Product.stock_quantity)
                ], else_=0)
            ).label('avg_turnover_ratio')
        ).filter(Product.stock_quantity > 0).scalar()
        
        return {
            "stock_overview": {
                "total_products": stock_overview.total_products,
                "total_stock": stock_overview.total_stock,
                "total_reserved": stock_overview.total_reserved,
                "available_stock": stock_overview.total_stock - stock_overview.total_reserved,
                "out_of_stock_count": stock_overview.out_of_stock,
                "low_stock_count": stock_overview.low_stock,
                "avg_stock_level": float(stock_overview.avg_stock_level or 0)
            },
            "stock_value_by_category": [
                {
                    "category": row.name,
                    "stock_value": float(row.stock_value or 0),
                    "product_count": row.product_count,
                    "avg_available": float(row.avg_available or 0)
                }
                for row in stock_value
            ],
            "movements_last_30_days": [
                {
                    "movement_type": row.movement_type.value,
                    "total_quantity": row.total_quantity,
                    "movement_count": row.movement_count
                }
                for row in movements
            ],
            "slow_moving_items": [
                {
                    "product_name": row.name,
                    "sku": row.sku,
                    "available_quantity": row.available_quantity,
                    "min_stock_level": row.min_stock_level,
                    "sales_last_30_days": row.sales_last_30_days
                }
                for row in slow_moving
            ],
            "stock_turnover_ratio": float(stock_turnover or 0)
        }
    
    def generate_dashboard_visualizations(self) -> Dict:
        """Generate Plotly visualizations for dashboard"""
        
        # Get sales data
        sales_data = self.get_sales_analytics("monthly")
        stock_data = self.get_stock_analytics()
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                'Ventes Mensuelles', 'Ventes par Type de Client',
                'Produits les Plus Vendus', 'Niveau de Stock',
                'Valeur du Stock par Catégorie', 'Mouvements de Stock'
            ),
            specs=[
                [{"type": "bar"}, {"type": "pie"}, {"type": "bar"}],
                [{"type": "gauge"}, {"type": "bar"}, {"type": "scatter"}]
            ]
        )
        
        # 1. Monthly sales bar chart
        periods = [item["period"] for item in sales_data["sales_trend"]]
        sales = [item["total_sales"] for item in sales_data["sales_trend"]]
        
        fig.add_trace(
            go.Bar(x=periods, y=sales, name="Ventes", marker_color='#3498DB'),
            row=1, col=1
        )
        
        # 2. Sales by client type pie chart
        client_types = [item["client_type"] for item in sales_data["sales_by_client_type"]]
        client_sales = [item["total_sales"] for item in sales_data["sales_by_client_type"]]
        
        fig.add_trace(
            go.Pie(labels=client_types, values=client_sales, hole=.3),
            row=1, col=2
        )
        
        # 3. Top products bar chart
        top_products = [item["product_name"][:15] + "..." for item in sales_data["top_products"][:5]]
        top_revenue = [item["total_revenue"] for item in sales_data["top_products"][:5]]
        
        fig.add_trace(
            go.Bar(x=top_products, y=top_revenue, name="Revenu", marker_color='#2ECC71'),
            row=1, col=3
        )
        
        # 4. Stock level gauge
        available_stock = stock_data["stock_overview"]["available_stock"]
        total_stock = stock_data["stock_overview"]["total_stock"]
        stock_percentage = (available_stock / total_stock * 100) if total_stock > 0 else 0
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=stock_percentage,
                title={'text': "Niveau de Stock"},
                gauge={'axis': {'range': [None, 100]},
                       'bar': {'color': "darkblue"},
                       'steps': [
                           {'range': [0, 30], 'color': "red"},
                           {'range': [30, 70], 'color': "yellow"},
                           {'range': [70, 100], 'color': "green"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                     'thickness': 0.75,
                                     'value': stock_data["stock_overview"]["avg_stock_level"]}}
            ),
            row=2, col=1
        )
        
        # 5. Stock value by category
        categories = [item["category"] for item in stock_data["stock_value_by_category"]]
        category_values = [item["stock_value"] for item in stock_data["stock_value_by_category"]]
        
        fig.add_trace(
            go.Bar(x=categories, y=category_values, name="Valeur Stock", marker_color='#E74C3C'),
            row=2, col=2
        )
        
        # 6. Stock movements scatter
        movement_types = [item["movement_type"] for item in stock_data["movements_last_30_days"]]
        movement_counts = [item["movement_count"] for item in stock_data["movements_last_30_days"]]
        
        fig.add_trace(
            go.Scatter(x=movement_types, y=movement_counts, mode='markers+lines',
                      name="Mouvements", marker=dict(size=10, color='#9B59B6')),
            row=2, col=3
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=False,
            title_text="Tableau de Bord Administratif - NOUR DISTRIBUTION",
            title_font_size=20
        )
        
        # Convert to JSON for frontend
        plot_json = json.loads(fig.to_json())
        
        # Generate KPIs
        kpis = {
            "total_revenue": sum(sales),
            "avg_monthly_sales": sum(sales) / len(sales) if sales else 0,
            "collection_rate": sales_data["payment_efficiency"]["collection_rate"],
            "total_tva_collected": sales_data["vat_analytics"]["total_tva_collected"],
            "out_of_stock_items": stock_data["stock_overview"]["out_of_stock_count"],
            "low_stock_items": stock_data["stock_overview"]["low_stock_count"],
            "stock_turnover_ratio": stock_data["stock_turnover_ratio"],
            #"total_orders_pending": self.db.query(func.count(Order.id)).filter(
                #Order.status == OrderStatus.EN_ATTENTE
            #).scalar()
        }
        
        return {
            "visualizations": plot_json,
            "kpis": kpis,
            "last_updated": datetime.utcnow().isoformat()
        }