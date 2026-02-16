# app/db/models/outbox.py
from sqlalchemy import Column, Index, String, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox"

    """Outbox record representing a domain event to be relayed to HQ.

    Each row carries a durable, ordered event with an idempotent event_id,
    typed metadata and a JSON payload. The relay process reads from this
    table and updates publish metadata without affecting the local write path.
    """

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    event_type = Column(String, nullable=False) # "SaleRecorded"
    aggregate_type = Column(String, nullable=False) # "Transaction"
    aggregate_id = Column(String, nullable=False)

    store_id = Column(String, nullable=False)


    payload = Column(JSONB, nullable=False)

    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    published_at = Column(DateTime(timezone=True), nullable=True)
    publish_attempts = Column(BigInteger, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_outbox_published_id", "published_at", "id"),
    )