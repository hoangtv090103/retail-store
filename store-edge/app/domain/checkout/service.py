# app/domain/checkout/service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select
from app.db.models.transactions import Transaction
from app.db.models.line_items import LineItem
from app.db.repositories.transactions import get_line_items_for_transaction, get_transaction_by_id
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

    txn = get_transaction_by_id(db, transaction_id)
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

async def recalculate_totals(
    db: AsyncSession,
    transaction_id: UUID
) -> Transaction:
    # Get transaction
    txn = get_transaction_by_id(db, transaction_id)

    if txn is None:
        raise ValueError("Transaction not found")
    
    # Get subtotal by SUM
    result_sum = await db.execute(
        select(func.coalesce(func.sum(LineItem.line_total), 0)).where(LineItem.transaction_id == transaction_id)
    )
    subtotal = result_sum.scalar()
    txn.subtotal = subtotal
    txn.total_amount = subtotal

    await db.commit()
    await db.refresh(txn)
    return txn

async def finalize_transaction(
    db: AsyncSession,
    transaction_id: UUID
) -> Transaction:
    txn = get_transaction_by_id(db, transaction_id)

    if txn is None:
        raise NotFoundError("Transaction not found")

    if txn.status != "DRAFT":
        raise BusinessError("Only DRAFT transactions can be finalized")
    
    items = await get_line_items_for_transaction(db, transaction_id)
    if not items:
        raise BusinessError("Cannot finalize empty transaction")

    # Recalculate totals
    txn = await recalculate_totals(db, transaction_id)

    txn.status = "PAID"

    await db.commit()
    await db.refresh(txn)

    return txn