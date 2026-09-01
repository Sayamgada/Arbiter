from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.demo import router as demo_router
from app.api.negotiation import router as negotiation_router
from app.core.database import engine
from app.core.redis import redis_client


app = FastAPI(
    title="Arbiter",
    description="Trust-Aware Revenue Negotiation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(negotiation_router)
app.include_router(demo_router)