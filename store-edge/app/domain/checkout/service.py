# app/domain/checkout/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from app.db.models.transactions import Transaction
from app.db.models.line_items import LineItem

from .schemas import AddItem, TransactionCreate

async def create_transaction(
    db: AsyncSession,
    data: TransactionCreate
) -> Transaction:
    txn = Transaction(
        store_id=data.store_id,
        terminal_id=data.terminal_id,
        cashier_id=data.cashier_id,
        status="DRAFT"
    )

    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn

async def add_item_to_transaction(
    db: AsyncSession,
    transaction_id,
    item: AddItem,
) -> LineItem:
    # Có thể thêm check transaction tồn tại, status = DRAFT
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        # với domain đúng, nên raise HTTPException ở layer API
        raise ValueError("Transaction not found")  # hoặc trả None cho route xử lý


    line_total = item.unit_price * item.quantity

    line = LineItem(
        transaction_id=transaction_id,
        sku_id=item.sku_id,
        barcode=item.barcode,
        product_name=item.product_name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=line_total,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line