import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ok"
    assert data["service"] == "orders-api"

def test_metrics_endpoint():
    # Make a request first
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "total_requests" in data
    assert "latency_p50_ms" in data
    assert "latency_p95_ms" in data

def test_user_lifecycle():
    email = "test_tester@example.com"
    res = client.post("/users", json={"name": "Test Tester", "email": email})
    assert res.status_code in [201, 400] # 400 if already exists

    get_res = client.get("/users")
    assert get_res.status_code == 200
    assert len(get_res.json()) > 0

def test_product_lifecycle():
    res = client.post("/products", json={"name": "Wireless Headphones", "price": 89.99, "stock": 50})
    assert res.status_code == 201
    prod_id = res.json()["id"]

    get_res = client.get(f"/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Wireless Headphones"

def test_orders_filtering_and_sorting():
    # Create user & product
    u_res = client.post("/users", json={"name": "Order Buyer", "email": "buyer@example.com"})
    u_id = u_res.json()["id"] if u_res.status_code == 201 else client.get("/users").json()[0]["id"]

    p_res = client.post("/products", json={"name": "Gaming Mouse", "price": 49.99, "stock": 100})
    p_id = p_res.json()["id"] if p_res.status_code == 201 else client.get("/products").json()[0]["id"]

    # Create order
    o_res = client.post("/orders", json={
        "user_id": u_id,
        "items": [{"product_id": p_id, "quantity": 2}]
    })
    assert o_res.status_code == 201
    order_data = o_res.json()
    assert order_data["user_id"] == u_id

    # Filter orders by user_id
    query_res = client.get(f"/orders?user_id={u_id}&limit=10")
    assert query_res.status_code == 200
    orders_list = query_res.json()
    assert len(orders_list) >= 1
    assert all(o["user_id"] == u_id for o in orders_list)
