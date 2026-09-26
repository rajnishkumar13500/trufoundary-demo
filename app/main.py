import time
import uuid
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
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
