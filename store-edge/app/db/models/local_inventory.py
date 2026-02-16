from sqlalchemy import Column, Index, Numeric, String, DateTime, BigInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import UUID, uuid4

from app.db.base import Base


class LocalInventory(Base):
    __tablename__ = "local_inventory"

    """Represents on-hand inventory quantities for a SKU at a store.

    Tracks the current stock levels (on hand, reserved and optional safety
    stock) for each (store, sku) pair, with timestamps that allow correlating
    inventory movements back to sales transactions and sync operations.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id = Column(String, nullable=False)
    sku = Column(String, nullable=False)

    on_hand = Column(Numeric(18, 3), nullable=False, default=0)
    reserved = Column(Numeric(18, 3), nullable=False, default=0)
    safety_stock = Column(Numeric(18, 3), nullable=True)

    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_txn_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_local_inventory_store_sku"),
        Index("ix_local_inventory_store_sku", "store_id", "sku"),
    )