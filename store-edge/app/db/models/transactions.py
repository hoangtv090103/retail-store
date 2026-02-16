from sqlalchemy import Column, Index, String, DateTime, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    """Represents a single POS transaction (receipt header) at a given store/terminal.

    A transaction aggregates one or more line items and optional payments, tracks
    its monetary totals (subtotal, tax, total), lifecycle timestamps, and basic
    contextual information such as store, terminal and cashier.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(String, nullable=False)
    terminal_id = Column(String, nullable=False)
    cashier_id = Column(String, nullable=True)
    
    receipt_number = Column(String, nullable=False)
    status = Column(String, nullable=False, default="DRAFT")

    subtotal = Column(Numeric(18, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(18, 2), nullable=False, default=0)
    total = Column(Numeric(18, 2), nullable=False, default=0)
    currency = Column(String, nullable=False, default="VND")

    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    client_created_at = Column(DateTime(timezone=True), nullable=True)

    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("store_id", "receipt_number", name="uq_transactions_store_receipt"),
        Index("ix_transactions_store_terminal_started", "store_id", "terminal_id", "started_at"),
    )