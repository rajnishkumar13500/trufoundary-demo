import time
import uuid
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app.metrics import metrics_collector
from app.routes.users import router as users_router
from app.routes.products import router as products_router
from app.routes.orders import router as orders_router

logger = logging.getLogger("actionshield.access")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema on startup if needed
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="ActionShield Demo API - Orders Service",
    description="Production-like eCommerce API for ActionShield self-validating agent demonstration",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    request.state.db_query_ms = 0.0

    start_time = time.perf_counter()
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        logger.error(f"Request failed: {exc}")
        response = JSONResponse(status_code=500, content={"error": "Internal Server Error"})

    total_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    db_ms = getattr(request.state, "db_query_ms", 0.0)

    # Record telemetry
    route = request.url.path
    metrics_collector.record_request(
        route=route,
        status_code=status_code,
        latency_ms=total_latency_ms,
        db_query_ms=db_ms
    )

    # Structured log line
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": request_id,
        "method": request.method,
        "route": route,
        "status_code": status_code,
        "latency_ms": total_latency_ms,
        "db_query_ms": db_ms
    }
    logger.info(json.dumps(log_entry))

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{total_latency_ms}ms"
    return response

@app.get("/", response_class=HTMLResponse, tags=["system"])
def root_ui():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ActionShield Demo App - Orders Service</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    body { background:#0a0d14; color:#f1f5f9; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }
    .card { background:#111622; border:1px solid #1e293b; border-radius:14px; max-width:640px; width:100%; padding:28px; box-shadow:0 20px 50px rgba(0,0,0,0.5); }
    .badge { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; }
    .badge-live { background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid rgba(34,197,94,0.3); }
    h1 { font-size:24px; margin-top:12px; margin-bottom:6px; color:#fff; }
    p { color:#94a3b8; font-size:14px; line-height:1.5; margin-bottom:20px; }
    .metric-box { background:#0d111a; border:1px solid #1e293b; border-radius:10px; padding:16px; margin-bottom:20px; display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .metric-label { font-size:11px; text-transform:uppercase; color:#64748b; font-weight:600; }
    .metric-val { font-size:22px; font-weight:800; font-family: 'JetBrains Mono', monospace; margin-top:4px; }
    .val-latency { color:#f59e0b; }
    .val-index { color:#38bdf8; }
    .btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:12px 20px; background:#6366f1; color:#fff; border:none; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:0.2s; }
    .btn:hover { background:#4f46e5; }
    .btn:disabled { opacity:0.6; cursor:not-allowed; }
    .results { margin-top:20px; background:#07090e; border:1px solid #1e293b; border-radius:8px; padding:14px; max-height:220px; overflow-y:auto; font-family: monospace; font-size:12px; color:#cbd5e1; }
    .links { margin-top:20px; display:flex; gap:12px; justify-content:center; font-size:13px; }
    .links a { color:#60a5fa; text-decoration:none; }
    .links a:hover { text-decoration:underline; }
  </style>
</head>
<body>
  <div class="card">
    <span class="badge badge-live">Live eCommerce Orders API</span>
    <h1>ActionShield Live Target App</h1>
    <p>This service simulates an orders database with high volume traffic. ActionShield monitors and automatically repairs performance bottlenecks.</p>

    <div class="metric-box">
      <div>
        <div class="metric-label">Last Query Latency</div>
        <div id="metric-latency" class="metric-val val-latency">-- ms</div>
      </div>
      <div>
        <div class="metric-label">Database Index</div>
        <div id="metric-status" class="metric-val val-index">Checking...</div>
      </div>
    </div>

    <button id="btn-query" class="btn" onclick="runQuery()">
      <span>⚡ Run Orders Query (user_id=1)</span>
    </button>

    <div id="results" class="results" style="display:none;"></div>

    <div class="links">
      <a href="/docs" target="_blank">Swagger API Docs</a>
      <span>&bull;</span>
      <a href="http://localhost:3000" target="_blank">ActionShield Dashboard</a>
      <span>&bull;</span>
      <a href="http://localhost:8790" target="_blank">TrueForge Studio</a>
    </div>
  </div>

  <script>
    async function checkIndex() {
      try {
        const res = await fetch('/health');
        const data = await res.json();
        document.getElementById('metric-status').textContent = 'Online';
      } catch(e) {
        document.getElementById('metric-status').textContent = 'Offline';
      }
    }
    checkIndex();

    async function runQuery() {
      const btn = document.getElementById('btn-query');
      const latencyEl = document.getElementById('metric-latency');
      const resultsEl = document.getElementById('results');
      btn.disabled = true;
      btn.textContent = '⏳ Executing Query...';
      
      const t0 = performance.now();
      try {
        const res = await fetch('/orders?user_id=1&limit=10');
        const data = await res.json();
        const t1 = performance.now();
        const elapsed = (t1 - t0).toFixed(2);
        
        latencyEl.textContent = elapsed + ' ms';
        if (elapsed > 500) {
          latencyEl.style.color = '#ef4444';
        } else {
          latencyEl.style.color = '#22c55e';
        }
        
        resultsEl.style.display = 'block';
        resultsEl.textContent = JSON.stringify(data.slice(0, 2), null, 2);
      } catch(err) {
        latencyEl.textContent = 'ERR';
        latencyEl.style.color = '#ef4444';
      } finally {
        btn.disabled = false;
        btn.textContent = '⚡ Run Orders Query (user_id=1)';
      }
    }
  </script>
</body>
</html>
"""

@app.get("/health", tags=["system"])
def health_check():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "service": "orders-api",
        "database": db_status,
        "version": "1.0.0"
    }

@app.get("/metrics", tags=["system"])
def get_metrics():
    return metrics_collector.get_snapshot()

app.include_router(users_router)
app.include_router(products_router)
app.include_router(orders_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
