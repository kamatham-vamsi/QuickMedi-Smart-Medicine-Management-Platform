"""Load sample data:  python -m app.seed"""
from datetime import date, timedelta

from . import crud, schemas
from .database import Base, SessionLocal, engine

today = date.today()

# name, generic, category, manufacturer, batch, qty, reorder level, price, days until expiry
SAMPLES = [
    ("Paracetamol 500mg", "Acetaminophen", "Analgesic", "Micro Labs", "PCM-2408", 240, 50, 1.20, 420),
    ("Amoxicillin 250mg", "Amoxicillin", "Antibiotic", "Cipla", "AMX-1173", 18, 40, 6.50, 210),
    ("Cetirizine 10mg", "Cetirizine", "Antihistamine", "Dr. Reddy's", "CTZ-0932", 95, 30, 2.10, 20),
    ("Metformin 500mg", "Metformin", "Antidiabetic", "Sun Pharma", "MET-5521", 300, 80, 1.85, 600),
    ("Pantoprazole 40mg", "Pantoprazole", "Antacid", "Alkem", "PAN-7710", 12, 25, 4.75, 300),
    ("ORS Sachet", "Oral rehydration salts", "Rehydration", "FDC", "ORS-0142", 60, 40, 8.00, -12),
    ("Azithromycin 500mg", "Azithromycin", "Antibiotic", "Zydus", "AZI-3390", 75, 30, 18.00, 15),
    ("Ibuprofen 400mg", "Ibuprofen", "Analgesic", "Abbott", "IBU-6604", 150, 40, 2.60, 510),
    ("Vitamin D3 60K", "Cholecalciferol", "Supplement", "Mankind", "VD3-8821", 8, 20, 22.00, 380),
    ("Betadine Ointment", "Povidone-iodine", "Antiseptic", "Win-Medicare", "BET-2210", 35, 15, 55.00, 700),
]


def run():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _, existing = crud.list_medicines(db, limit=1)
        if existing:
            print(f"Skipped: database already has {existing} medicines.")
            return
        for name, generic, cat, maker, batch, qty, reorder, price, days in SAMPLES:
            crud.create_medicine(
                db,
                schemas.MedicineCreate(
                    name=name,
                    generic_name=generic,
                    category=cat,
                    manufacturer=maker,
                    batch_number=batch,
                    quantity=qty,
                    reorder_level=reorder,
                    unit_price=price,
                    expiry_date=today + timedelta(days=days),
                ),
            )
        print(f"Seeded {len(SAMPLES)} medicines.")


if __name__ == "__main__":
    run()
