# app/domain/checkout/schemas.py
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class TransactionCreate(BaseModel):
    store_id: str
    terminal_id: str
    cashier_id: Optional[str] = None

class AddItem(BaseModel):
    sku_id: str
    barcode: str
    product_name: str
    quantity: int
    unit_price: float

class LineItemOut(BaseModel):
    id: UUID
    sku_id: str
    barcode: str
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True

class TransactionOut(BaseModel):
    id: UUID
    store_id: str
    terminal_id: str
    cashier_id: Optional[str]
    status: str

    class Config:
        from_attributes = True  # hoặc orm_mode = True tùy version Pydantic

