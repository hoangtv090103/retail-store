
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.db.models.transactions import Transaction
from app.db.models.line_items import LineItem

async def get_transaction_by_id(
    db: AsyncSession,
    transaction_id: UUID
) -> Transaction:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    return txn

async def get_line_items_for_transaction(
    db: AsyncSession,
    transaction_id: UUID
) -> List[LineItem]:
    result = await db.execute(
        select(LineItem).where(LineItem.transaction_id == transaction_id)
    )
    line_items = result.scalars.all()
    return line_items