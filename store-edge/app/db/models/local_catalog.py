# app/db/models/local_catalog.py
from sqlalchemy import Boolean, Column, Integer, Numeric, String, DateTime, BigInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class LocalCatalog(Base):
    __tablename__ = "local_catalog"

    """Represents the local product catalog snapshot for a given store.

    Each row defines a sellable SKU (with optional barcode), its pricing,
    tax configuration and basic descriptive attributes as they are known
    at the edge node, independent of the upstream HQ representation.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id = Column(String, nullable=False, index=True)

    sku = Column(String, nullable=False)
    barcode = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)

    price = Column(Numeric(18, 2), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=True)
    uom = Column(String, nullable=False, default="EA")

    active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("store_id", "sku", name="uq_local_catalog_store_sku"),
    )