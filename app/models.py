from datetime import date, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

EXPIRY_WARNING_DAYS = 30


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    generic_name: Mapped[str | None] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="General", index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(150))
    batch_number: Mapped[str | None] = mapped_column(String(60))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    expiry_date: Mapped[date] = mapped_column(nullable=False, index=True)
    storage_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="medicine",
        cascade="all, delete-orphan",
        order_by="StockMovement.id.desc()",
    )

    @property
    def status(self) -> str:
        today = date.today()
        if self.expiry_date < today:
            return "expired"
        if self.expiry_date <= today + timedelta(days=EXPIRY_WARNING_DAYS):
            return "expiring"
        if self.quantity <= self.reorder_level:
            return "low_stock"
        return "ok"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    medicine: Mapped[Medicine] = relationship(back_populates="movements")
