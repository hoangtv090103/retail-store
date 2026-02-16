
from sqlalchemy import Column, String, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.base import Base


class SyncCursor(Base):
    __tablename__ = "sync_cursors"

    """Tracks progress of asynchronous synchronization streams.

    A sync cursor stores the last successfully processed outbox id and
    associated metadata for a named stream, allowing idempotent and
    restartable edge→HQ replay without scanning the entire outbox.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stream_name = Column(String, nullable=False, unique=True)

    last_outbox_id = Column(BigInteger, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())