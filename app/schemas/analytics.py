from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

# Dashboard Response
class DashboardStats(BaseModel):
    """Main dashboard statistics"""
    # Revenue
    total_revenue_this_month: float = Field(description="Total revenue for current month (paid factures)")
    revenue_vs_last_month_percent: float = Field(description="Revenue change % compared to last month")
    
    # Orders
    total_orders: int = Field(description="Total orders count")
    pending_orders: int = Field(description="Orders awaiting processing")
    completed_orders: int = Field(description="Successfully completed orders")
    cancelled_orders: int = Field(description="Cancelled orders")
    
    # Clients
    active_clients: int = Field(description="Total active clients")
    
    # Inventory
    low_stock_items: int = Field(description="Products below minimum stock threshold")
    
    # Payments
    outstanding_payments: float = Field(description="Total unpaid facture amount")
    unpaid_factures_count: int = Field(description="Number of unpaid factures")

# Period Sales Data
class PeriodSales(BaseModel):
    """Sales data for a specific period"""
    period: str = Field(description="Period label (e.g., '2023-12-01', 'Week 50')")
    revenue: float
    orders_count: int
    average_order_value: float

# Sales Analytics
class SalesAnalytics(BaseModel):
    """Sales analytics over time"""
    start_date: datetime
    end_date: datetime
    total_revenue: float
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    average_order_value: float
    sales_by_period: List[PeriodSales]

# Revenue by Category
class CategoryRevenue(BaseModel):
    """Revenue breakdown by category"""
    category_id: Optional[UUID] = None
    category_name: str
    total_revenue: float
    orders_count: int
    products_count: int

# Revenue Analytics
class RevenueAnalytics(BaseModel):
    """Revenue analytics breakdown"""
    total_revenue: float
    paid_revenue: float
    unpaid_revenue: float
    revenue_by_category: List[CategoryRevenue]
    revenue_by_client_type: Dict[str, float] = Field(description="B2B vs B2C revenue")

# Top Product
class TopProduct(BaseModel):
    """Top selling product"""
    model_config = ConfigDict(from_attributes=True)
    
    product_id: UUID
    product_name: str
    sku: str
    total_quantity_sold: int
    total_revenue: float
    orders_count: int
    category_name: Optional[str] = None

# Low Stock Product
class LowStockProduct(BaseModel):
    """Product with low stock"""
    model_config = ConfigDict(from_attributes=True)
    
    product_id: UUID
    product_name: str
    sku: str
    current_stock: int
    reserved_stock: int
    available_stock: int
    category_name: Optional[str] = None

# Top Client
class TopClient(BaseModel):
    """Top client by revenue"""
    client_id: UUID
    client_name: str
    client_type: str
    total_revenue: float
    orders_count: int
    factures_count: int
    average_order_value: float

# Client Overview
class ClientOverview(BaseModel):
    """Client statistics overview"""
    total_clients: int
    b2b_clients: int
    b2c_clients: int
    active_clients_this_month: int
    new_clients_this_month: int

# Devis Conversion
class DevisConversion(BaseModel):
    """Devis to facture conversion metrics"""
    total_devis: int
    accepted_devis: int
    converted_to_facture: int
    cancelled_devis: int
    pending_devis: int
    conversion_rate: float = Field(description="Percentage of devis converted to factures")
    acceptance_rate: float = Field(description="Percentage of devis accepted")

# Payment Statistics
class PaymentStatistics(BaseModel):
    """Payment collection statistics"""
    total_factures: int
    paid_factures: int
    partially_paid_factures: int
    unpaid_factures: int
    total_billed: float
    total_collected: float
    total_outstanding: float
    collection_rate: float = Field(description="Percentage of billed amount collected")

# --- Advanced Financial Analytics ---

class FinancialSummary(BaseModel):
    revenue: float
    revenue_change_percent: float
    expenses: float
    expenses_change_percent: float
    profit: float
    profit_change_percent: float
    margin: float
    margin_change_percent: float

class FinancialTrend(BaseModel):
    month: str
    revenue: float
    expenses: float
    profit: float
    margin: float

class FinancialAnalyticsResponse(BaseModel):
    summary: FinancialSummary
    trend: List[FinancialTrend]

class ExpenseCategory(BaseModel):
    category: str
    amount: float
    percentage: float
    trend: str  # "up", "down", "stable"

class RevenueSource(BaseModel):
    name: str
    amount: float
    source: str
    accuracy: str  # "high", "medium", "low"

class ExpenseBreakdown(BaseModel):
    categories: List[ExpenseCategory]
    sources: List[RevenueSource]

class MonthComparison(BaseModel):
    month: str
    thisYear: float
    lastYear: float

class SmartInsights(BaseModel):
    insights: List[str]
