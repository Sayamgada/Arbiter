from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import redis_client


app = FastAPI(
    title="Arbiter",
    description="Trust-Aware Revenue Negotiation",
    version="0.1.0",
)


@app.get("/health")
async def health():
    postgres_status = "ok"
    redis_status = "ok"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        postgres_status = "error"

    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    overall_status = (
        "ok"
        if postgres_status == "ok" and redis_status == "ok"
        else "degraded"
    )

    return {
        "status": overall_status,
        "service": "arbiter",
        "dependencies": {
            "postgres": postgres_status,
            "redis": redis_status,
        },
    }