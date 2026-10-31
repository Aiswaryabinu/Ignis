"""Pydantic schemas for dashboard."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RecentQuotation(BaseModel):
    quotation_number: str
    customer_name: str | None = None
    total: Decimal
    status: str
    created_at: datetime


class TopProduct(BaseModel):
    name: str
    category_name: str | None = None
    total_sold: Decimal


class DashboardSummary(BaseModel):
    totalCustomers: int
    totalProducts: int
    pendingQuotations: int
    monthlyRevenue: Decimal
    recentQuotations: list[RecentQuotation]
    topProducts: list[TopProduct]
