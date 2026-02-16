# app/api/v1/routes_checkout.py
from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.base import get_db 
from app.domain.checkout.schemas import AddItem, LineItemOut, TransactionCreate, TransactionOut
from app.domain.checkout.service import add_item_to_transaction, create_transaction


router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


@router.post("", response_model=TransactionOut)
async def create_transaction_endpoint(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    txn = await create_transaction(db, payload)
    return txn

@router.post("/{transaction_id}/items", response_model=LineItemOut)
async def add_item_endpoint(
    transaction_id: UUID,
    payload: AddItem,
    db: AsyncSession = Depends(get_db),
):
    # ở bước sau có thể thêm check txn thuộc store/terminal hiện tại
    line = await add_item_to_transaction(db, transaction_id, payload)
    return line