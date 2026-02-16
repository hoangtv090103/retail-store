# app/db/models/outbox.py
from enum import unique
from sqlalchemy import Column, String, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base

class OutboxEvent(Base):
    __tablename__ = "outbox"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    event_type = Column(String, nullable=False) # "SaleRecorded"
    aggregate_type = Column(String, nullable=False) # "Transaction"
    aggregate_id = Column(String, nullable=False)

    payload = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    publish_attempts = Column(BigInteger, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
