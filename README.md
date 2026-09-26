# ActionShield Demo App --- Orders Service

A production-like FastAPI & PostgreSQL eCommerce service designed for the TrueFoundry **ActionShield** self-validating autonomous engineering agent demonstration.

---

## 1. Quickstart

### Local Setup (SQLite or Postgres)
```bash
# Install dependencies
pip install -r requirements.txt

# Seed 25,000 orders
python scripts/seed_db.py 25000

# Start server on http://localhost:8000
python app/main.py
```

### Docker Compose (Production Environment)
```bash
docker compose up -d --build
docker compose exec api python scripts/seed_db.py 25000
```

---

## 2. Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service and database health check |
| `GET` | `/metrics` | Real-time p50, p95, throughput, error rates |
| `GET` | `/orders?user_id=1&limit=50` | Filter orders (the target slow endpoint) |
| `GET` | `/orders/{id}` | Order details |
| `POST` | `/orders` | Place new order |
| `GET` | `/products` | Product catalog |
| `GET` | `/users` | Customer directory |

---

## 3. The Target Incident: Slow Orders API

Query:
```sql
SELECT * FROM orders WHERE user_id = :uid ORDER BY created_at DESC;
```

In the initial unindexed state with 25,000+ orders, every request forces a sequential table scan and external filesort.

### Reproducing Baseline Performance
Run the benchmark load test:
```bash
python scripts/load_test.py --url http://localhost:8000 -n 100 -c 10
```

### Applying the Validated Fix
```bash
python scripts/migrate.py migrations/002_add_orders_index.sql
```

### Re-running Benchmark
```bash
python scripts/load_test.py --url http://localhost:8000 -n 100 -c 10
```
Notice the dramatic reduction in p95 latency from seconds down to milliseconds.

### Rollback (If needed)
```bash
python scripts/migrate.py migrations/002_rollback.sql
```

---

## 4. Automated Tests
```bash
pytest tests/ -v
```
