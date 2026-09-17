"""
DBPTBS - FastAPI Application
-------------------------------
Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database as db
from app import engine
from app.api.routes import router

app = FastAPI(
    title="DBPTBS - DNA Behavioural Pre-Transaction Blockchain Security System",
    description=(
        "A behavioural risk-assessment and pre-transaction security layer that detects deviations "
        "from a user's established behavioural profile and triggers additional verification before "
        "simulated blockchain execution. Hackathon prototype - all wallets, transactions, and "
        "behavioural data are simulated/synthetic."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    db.init_db()
    # Pre-warm the default demo user so the very first request in a live
    # demo isn't slowed down by history generation + model fitting.
    engine.get_session("USR001")


@app.get("/")
def root():
    return {
        "system": "DBPTBS",
        "status": "PROTECTED",
        "docs": "/docs",
        "note": "Prototype - simulated wallets and behavioural data only.",
    }
