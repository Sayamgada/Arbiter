from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.demo import router as demo_router
from app.api.negotiation import router as negotiation_router
from app.core.database import engine
from app.core.redis import redis_client
import os

app = FastAPI(
    title="Arbiter",
    description="Trust-Aware Revenue Negotiation",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {"status": "ok"}

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(negotiation_router)
app.include_router(demo_router)