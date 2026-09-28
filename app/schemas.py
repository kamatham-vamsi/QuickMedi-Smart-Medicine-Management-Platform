from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["ok", "low_stock", "expiring", "expired"]


class MedicineBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    generic_name: str | None = Field(default=None, max_length=150)
    category: str = Field(default="General", min_length=1, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=150)
    batch_number: str | None = Field(default=None, max_length=60)
    quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    unit_price: float = Field(default=0, ge=0)
    expiry_date: date
    storage_notes: str | None = None


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    generic_name: str | None = Field(default=None, max_length=150)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=150)
    batch_number: str | None = Field(default=None, max_length=60)
    quantity: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    expiry_date: date | None = None
    storage_notes: str | None = None


class MedicineOut(MedicineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Status
    created_at: datetime
    updated_at: datetime


class MedicineList(BaseModel):
    items: list[MedicineOut]
    total: int


class StockAdjust(BaseModel):
    change: int = Field(description="Positive to add stock, negative to remove")
    reason: str | None = Field(default=None, max_length=200)


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medicine_id: int
    change: int
    reason: str | None
    created_at: datetime


class Stats(BaseModel):
    total: int
    low_stock: int
    expiring: int
    expired: int
    stock_value: float
