"""Quotation and QuotationItem models."""

import uuid
from datetime import datetime, date, timezone
from decimal import Decimal

from sqlalchemy import String, Text, ForeignKey, Numeric, Enum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL")
    )
    quotation_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "draft", "sent", "accepted", "rejected", "expired", "converted",
            name="quotation_status", create_type=False,
        ),
        default="draft",
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    company = relationship("Company", back_populates="quotations")
    customer = relationship("Customer")
    creator = relationship("User", foreign_keys=[created_by])
    items = relationship(
        "QuotationItem", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_type: Mapped[str | None] = mapped_column(
        Enum("percentage", "fixed", name="discount_type", create_type=False)
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    tax_rate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tax_rates.id")
    )
    tax_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product")
