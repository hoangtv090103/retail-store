
import enum
from sqlalchemy import Column, Enum, ForeignKey, Numeric, String, DateTime, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Payment(Base):
    __tablename__ = "paymemts"

    """Represents the payment attached to a transaction.

    This model stores how a transaction was paid (provider/method), the amount,
    current payment status (pending/captured/failed, etc.) and any provider
    specific references or payloads required for reconciliation.
    """

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), unique=True)
    provider = Column(Text)
    
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="VND")
    status = Column(Enum(PaymentStatus, name="payment_status_enum"), nullable=False, default=PaymentStatus.PENDING)  # PENDING, CAPTURED...

    provider_ref = Column(String, nullable=True, index=True)
    qr_payload = Column(JSONB, nullable=True)

    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())