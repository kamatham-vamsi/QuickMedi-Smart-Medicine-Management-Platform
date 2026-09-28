from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import Base, engine, get_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="QuickMedi API",
    description="Smart medicine management: inventory, expiry tracking and stock movements.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_or_404(db: Session, medicine_id: int) -> models.Medicine:
    medicine = crud.get_medicine(db, medicine_id)
    if medicine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Medicine {medicine_id} not found")
    return medicine


@app.get("/api/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/stats", response_model=schemas.Stats, tags=["dashboard"])
def stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)


@app.get("/api/categories", response_model=list[str], tags=["medicines"])
def categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)


@app.get("/api/medicines", response_model=schemas.MedicineList, tags=["medicines"])
def list_medicines(
    search: str | None = None,
    category: str | None = None,
    status_filter: schemas.Status | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    items, total = crud.list_medicines(db, search, category, status_filter, skip, limit)
    return {"items": items, "total": total}


@app.post(
    "/api/medicines",
    response_model=schemas.MedicineOut,
    status_code=status.HTTP_201_CREATED,
    tags=["medicines"],
)
def create_medicine(data: schemas.MedicineCreate, db: Session = Depends(get_db)):
    return crud.create_medicine(db, data)


@app.get("/api/medicines/{medicine_id}", response_model=schemas.MedicineOut, tags=["medicines"])
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, medicine_id)


@app.put("/api/medicines/{medicine_id}", response_model=schemas.MedicineOut, tags=["medicines"])
def update_medicine(medicine_id: int, data: schemas.MedicineUpdate, db: Session = Depends(get_db)):
    return crud.update_medicine(db, _get_or_404(db, medicine_id), data)


@app.delete(
    "/api/medicines/{medicine_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["medicines"]
)
def delete_medicine(medicine_id: int, db: Session = Depends(get_db)):
    crud.delete_medicine(db, _get_or_404(db, medicine_id))


@app.post(
    "/api/medicines/{medicine_id}/stock", response_model=schemas.MedicineOut, tags=["stock"]
)
def adjust_stock(medicine_id: int, data: schemas.StockAdjust, db: Session = Depends(get_db)):
    if data.change == 0:
        raise HTTPException(422, "Change must not be zero")
    medicine = _get_or_404(db, medicine_id)
    try:
        return crud.adjust_stock(db, medicine, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@app.get(
    "/api/medicines/{medicine_id}/movements",
    response_model=list[schemas.StockMovementOut],
    tags=["stock"],
)
def movements(medicine_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, medicine_id).movements


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
