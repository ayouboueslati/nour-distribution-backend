from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.api.v1.deps import require_manager
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    DashboardStats, SalesAnalytics, RevenueAnalytics,
    TopProduct, TopClient, ClientOverview,
    DevisConversion, PaymentStatistics, LowStockProduct,
    FinancialAnalyticsResponse, ExpenseBreakdown, MonthComparison, SmartInsights
)

router = APIRouter()

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get main dashboard statistics - Manager+ only
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_dashboard_stats()

@router.get("/financials", response_model=FinancialAnalyticsResponse)
async def get_financial_metrics(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get advanced financial metrics (Revenue, Expenses, Profit, Margin) - Manager+ only
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_financial_metrics(period=period)

@router.get("/expenses/breakdown", response_model=ExpenseBreakdown)
async def get_expense_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get detailed breakdown of business expenses - Manager+ only
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_expense_breakdown()

@router.get("/comparison", response_model=List[MonthComparison])
async def get_yearly_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get yearly comparative performance (Current Year vs Last Year) - Manager+ only
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_comparative_performance()

@router.get("/insights", response_model=SmartInsights)
async def get_smart_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get automated business insights based on performance trends - Manager+ only
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_smart_insights()

@router.get("/sales")
async def get_sales_analytics(
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get sales analytics with trends - Manager+ only
    Period options: daily, weekly, monthly
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_sales_analytics(period=period)

@router.get("/stock")
async def get_stock_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get comprehensive stock analytics - Manager+ only
    Includes stock levels, value by category, movements, and slow-moving items
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_stock_analytics()

@router.get("/visualizations")
async def get_dashboard_visualizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get dashboard visualizations (Plotly charts) - Manager+ only
    Returns JSON for rendering charts in frontend
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.generate_dashboard_visualizations()