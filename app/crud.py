from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import models, schemas
from .models import EXPIRY_WARNING_DAYS


def _status_clause(status: str, today: date):
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    M = models.Medicine
    if status == "expired":
        return M.expiry_date < today
    if status == "expiring":
        return (M.expiry_date >= today) & (M.expiry_date <= soon)
    if status == "low_stock":
        return (M.expiry_date > soon) & (M.quantity <= M.reorder_level)
    if status == "ok":
        return (M.expiry_date > soon) & (M.quantity > M.reorder_level)
    return None


def list_medicines(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    M = models.Medicine
    stmt = select(M)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(M.name.like(like), M.generic_name.like(like), M.batch_number.like(like))
        )
    if category:
        stmt = stmt.where(M.category == category)
    if status:
        clause = _status_clause(status, date.today())
        if clause is not None:
            stmt = stmt.where(clause)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(M.expiry_date, M.name).offset(skip).limit(limit)).all()
    return items, total


def get_medicine(db: Session, medicine_id: int):
    return db.get(models.Medicine, medicine_id)


def create_medicine(db: Session, data: schemas.MedicineCreate):
    medicine = models.Medicine(**data.model_dump())
    db.add(medicine)
    db.flush()
    if medicine.quantity:
        db.add(
            models.StockMovement(
                medicine_id=medicine.id, change=medicine.quantity, reason="Opening stock"
            )
        )
    db.commit()
    db.refresh(medicine)
    return medicine


def update_medicine(db: Session, medicine: models.Medicine, data: schemas.MedicineUpdate):
    changes = data.model_dump(exclude_unset=True)
    # Non-nullable columns must never be set to None
    for required in ("name", "category", "quantity", "reorder_level", "unit_price", "expiry_date"):
        if required in changes and changes[required] is None:
            changes.pop(required)
    old_qty = medicine.quantity
    for field, value in changes.items():
        setattr(medicine, field, value)
    if medicine.quantity != old_qty:
        db.add(
            models.StockMovement(
                medicine_id=medicine.id,
                change=medicine.quantity - old_qty,
                reason="Edited in medicine form",
            )
        )
    db.commit()
    db.refresh(medicine)
    return medicine


def delete_medicine(db: Session, medicine: models.Medicine):
    db.delete(medicine)
    db.commit()


def adjust_stock(db: Session, medicine: models.Medicine, data: schemas.StockAdjust):
    new_qty = medicine.quantity + data.change
    if new_qty < 0:
        raise ValueError(f"Only {medicine.quantity} in stock; cannot remove {abs(data.change)}.")
    medicine.quantity = new_qty
    db.add(models.StockMovement(medicine_id=medicine.id, change=data.change, reason=data.reason))
    db.commit()
    db.refresh(medicine)
    return medicine


def get_stats(db: Session) -> dict:
    today = date.today()
    M = models.Medicine

    def count(status: str) -> int:
        return db.scalar(select(func.count()).select_from(M).where(_status_clause(status, today))) or 0

    total = db.scalar(select(func.count()).select_from(M)) or 0
    value = db.scalar(select(func.coalesce(func.sum(M.quantity * M.unit_price), 0))) or 0
    return {
        "total": total,
        "low_stock": count("low_stock"),
        "expiring": count("expiring"),
        "expired": count("expired"),
        "stock_value": float(value),
    }


def list_categories(db: Session) -> list[str]:
    return list(
        db.scalars(select(models.Medicine.category).distinct().order_by(models.Medicine.category))
    )
