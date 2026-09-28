# QuickMedi – Smart Medicine Management Platform

Full-stack medicine inventory app: a **FastAPI + MySQL** backend with a lightweight web dashboard.
Tracks stock, batch numbers, expiry dates, low-stock alerts and every stock movement.

**Tech stack:** Python · FastAPI · SQLAlchemy · MySQL (SQLite for quick local runs) · REST APIs · HTML/CSS/JavaScript · Docker · pytest · GitHub Actions

## Features
- CRUD for medicines (name, generic name, category, manufacturer, batch, price, expiry, storage notes)
- Automatic status: **In stock**, **Low stock** (at or below reorder level), **Expiring soon** (30 days), **Expired**
- Dashboard counts that double as filters, plus search (name / generic / batch) and category filter
- Stock in/out with reason, and a full movement history per medicine
- Input validation (Pydantic), clear error messages, auto-generated API docs at `/docs`
- Automated tests (pytest) and CI on every push

## Run locally

### Option 1: Docker (MySQL included)
```bash
docker compose up --build
# open http://localhost:8000
```

### Option 2: Python + your own MySQL
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # set DATABASE_URL for your MySQL
# optional: mysql -u root -p < sql/schema.sql
python -m app.seed                                       # optional sample data
uvicorn app.main:app --reload
```
Leave `DATABASE_URL` unset to use a local SQLite file instead. Open http://localhost:8000 and API docs at http://localhost:8000/docs.

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/medicines?search=&category=&status=` | List and filter |
| POST | `/api/medicines` | Add medicine |
| GET / PUT / DELETE | `/api/medicines/{id}` | Read, update, delete |
| POST | `/api/medicines/{id}/stock` | Add or remove stock (`{"change": -5, "reason": "Dispensed"}`) |
| GET | `/api/medicines/{id}/movements` | Stock history |
| GET | `/api/stats` | Totals, alerts, stock value |
| GET | `/api/categories` | Distinct categories |
| GET | `/api/health` | Health check (verifies DB) |

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```

## Project structure
```
app/
  main.py       routes and app setup
  models.py     SQLAlchemy models
  schemas.py    Pydantic request/response models
  crud.py       database operations
  seed.py       sample data
  static/       web dashboard (HTML, CSS, JS)
sql/schema.sql  reference MySQL schema
tests/          API tests
```

## Author
Vamsi – Backend Developer
