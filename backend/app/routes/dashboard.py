"""Dashboard route: summary statistics."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.models.catalog import Product, Category
from app.models.quotation import Quotation, QuotationItem
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.dashboard import DashboardSummary, RecentQuotation, TopProduct
from app.utils.deps import CurrentUser

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(user: CurrentUser, db: Session = Depends(get_db)):
    """Return aggregated stats scoped to the current user's company."""
    cid = user.company_id

    total_customers = (
        db.query(func.count(Customer.id))
        .filter(Customer.company_id == cid, Customer.is_active.is_(True))
        .scalar()
    ) or 0

    total_products = (
        db.query(func.count(Product.id))
        .filter(Product.company_id == cid, Product.is_active.is_(True))
        .scalar()
    ) or 0

    pending_quotations = (
        db.query(func.count(Quotation.id))
        .filter(
            Quotation.company_id == cid,
            Quotation.status.in_(["draft", "sent"]),
        )
        .scalar()
    ) or 0

    # Monthly revenue: sum of paid invoices this month
    now = datetime.now(timezone.utc)
    monthly_revenue = (
        db.query(func.coalesce(func.sum(Invoice.total), 0))
        .filter(
            Invoice.company_id == cid,
            Invoice.status == "paid",
            extract("year", Invoice.created_at) == now.year,
            extract("month", Invoice.created_at) == now.month,
        )
        .scalar()
    ) or Decimal("0")

    # Recent quotations (last 5)
    recent_rows = (
        db.query(Quotation)
        .filter(Quotation.company_id == cid)
        .order_by(Quotation.created_at.desc())
        .limit(5)
        .all()
    )
    recent_quotations = [
        RecentQuotation(
            quotation_number=q.quotation_number,
            customer_name=q.customer.name if q.customer else None,
            total=q.total,
            status=q.status,
            created_at=q.created_at,
        )
        for q in recent_rows
    ]

    # Top products by total quantity sold across quotation items
    top_rows = (
        db.query(
            Product.name,
            Category.name.label("category_name"),
            func.coalesce(func.sum(QuotationItem.quantity), 0).label("total_sold"),
        )
        .join(QuotationItem, QuotationItem.product_id == Product.id, isouter=True)
        .join(Category, Category.id == Product.category_id, isouter=True)
        .filter(Product.company_id == cid)
        .group_by(Product.id, Product.name, Category.name)
        .order_by(func.coalesce(func.sum(QuotationItem.quantity), 0).desc())
        .limit(5)
        .all()
    )
    top_products = [
        TopProduct(name=r.name, category_name=r.category_name, total_sold=r.total_sold)
        for r in top_rows
    ]

    return DashboardSummary(
        totalCustomers=total_customers,
        totalProducts=total_products,
        pendingQuotations=pending_quotations,
        monthlyRevenue=monthly_revenue,
        recentQuotations=recent_quotations,
        topProducts=top_products,
    )
