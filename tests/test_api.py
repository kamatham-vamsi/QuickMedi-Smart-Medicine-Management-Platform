from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def payload(**overrides):
    data = {
        "name": "Paracetamol 500mg",
        "generic_name": "Acetaminophen",
        "category": "Analgesic",
        "batch_number": "PCM-1",
        "quantity": 100,
        "reorder_level": 20,
        "unit_price": 1.5,
        "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
    }
    data.update(overrides)
    return data


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_and_get(client):
    res = client.post("/api/medicines", json=payload())
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ok"
    assert client.get(f"/api/medicines/{body['id']}").json()["name"] == "Paracetamol 500mg"


def test_validation_rejects_negative_quantity(client):
    assert client.post("/api/medicines", json=payload(quantity=-1)).status_code == 422


def test_not_found(client):
    assert client.get("/api/medicines/999").status_code == 404


def test_update_and_delete(client):
    mid = client.post("/api/medicines", json=payload()).json()["id"]
    res = client.put(f"/api/medicines/{mid}", json={"name": "Dolo 650", "quantity": 80})
    assert res.status_code == 200 and res.json()["name"] == "Dolo 650"
    moves = client.get(f"/api/medicines/{mid}/movements").json()
    assert moves[0]["change"] == -20
    assert client.delete(f"/api/medicines/{mid}").status_code == 204
    assert client.get(f"/api/medicines/{mid}").status_code == 404


def test_status_rules_and_filters(client):
    today = date.today()
    client.post("/api/medicines", json=payload(name="Fine"))
    client.post("/api/medicines", json=payload(name="Low", quantity=5))
    client.post("/api/medicines", json=payload(name="Soon", expiry_date=(today + timedelta(days=10)).isoformat()))
    client.post("/api/medicines", json=payload(name="Old", expiry_date=(today - timedelta(days=1)).isoformat()))

    def names(status):
        items = client.get("/api/medicines", params={"status": status}).json()["items"]
        return {m["name"] for m in items}

    assert names("ok") == {"Fine"}
    assert names("low_stock") == {"Low"}
    assert names("expiring") == {"Soon"}
    assert names("expired") == {"Old"}

    stats = client.get("/api/stats").json()
    assert stats["total"] == 4 and stats["low_stock"] == 1
    assert stats["expiring"] == 1 and stats["expired"] == 1


def test_search_and_category(client):
    client.post("/api/medicines", json=payload(name="Amoxicillin", category="Antibiotic", batch_number="AMX9"))
    client.post("/api/medicines", json=payload(name="Ibuprofen"))
    assert client.get("/api/medicines", params={"search": "amox"}).json()["total"] == 1
    assert client.get("/api/medicines", params={"search": "AMX9"}).json()["total"] == 1
    assert client.get("/api/medicines", params={"category": "Analgesic"}).json()["total"] == 1
    assert set(client.get("/api/categories").json()) == {"Antibiotic", "Analgesic"}


def test_stock_adjustment(client):
    mid = client.post("/api/medicines", json=payload(quantity=10)).json()["id"]
    res = client.post(f"/api/medicines/{mid}/stock", json={"change": 15, "reason": "Delivery"})
    assert res.json()["quantity"] == 25
    res = client.post(f"/api/medicines/{mid}/stock", json={"change": -100})
    assert res.status_code == 400
    assert client.post(f"/api/medicines/{mid}/stock", json={"change": 0}).status_code == 422
    changes = [m["change"] for m in client.get(f"/api/medicines/{mid}/movements").json()]
    assert changes == [15, 10]


def test_frontend_served(client):
    res = client.get("/")
    assert res.status_code == 200 and "QuickMedi" in res.text
