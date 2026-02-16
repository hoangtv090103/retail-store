from sqlalchemy import Column, Index, String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class LineItem(Base):
    __tablename__ = "line_items"

    """Represents a single product line within a transaction.

    A line item captures the SKU/barcode, display name, pricing information
    (unit price, discounts, tax) and quantity at the time of sale so that
    reporting and auditing do not depend on the mutable catalog state.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    line_number = Column(Integer, nullable=False)

    sku = Column(String, nullable=False, index=True)
    barcode = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)

    unit_price = Column(Numeric(18, 2), nullable=False)
    quantity = Column(Numeric(18, 3), nullable=False, default=1)
    discount_amount = Column(Numeric(18, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(18, 2), nullable=False, default=0)
    line_total = Column(Numeric(18, 2), nullable=False)

    uom = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_line_items_transaction_line", "transaction_id", "line_number", unique=True),
    )