"""
DBPTBS - FastAPI Application
-------------------------------
Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import database as db
from app import engine
from app.api.routes import router
from app.config import ALLOWED_ORIGINS, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

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

# Restricted to known dashboard origins rather than "*" - see app/config.py.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Demo-grade rate limiting (stdlib only - fixed window per client IP).
# Not a substitute for a real gateway/WAF in production, but stops naive
# flooding of a publicly reachable demo without adding a dependency.
# ---------------------------------------------------------------------------
_request_log: dict[str, deque] = defaultdict(deque)
_rate_lock = threading.Lock()


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    with _rate_lock:
        window = _request_log[client_ip]
        while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
            window.popleft()
        if len(window) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests - please slow down (demo-grade rate limit)."},
            )
        window.append(now)
    return await call_next(request)


app.include_router(router)


@app.on_event("startup")
def on_startup():
    # Wipes any leftover demo data from a previous run so the API always
    # starts with a clean slate - see app/database.py:ensure_fresh_start.
    db.ensure_fresh_start()
    # Pre-warm the default demo user so the very first request in a live
    # demo isn't slowed down by history generation + model fitting.
    engine.get_session("USR001")


@app.get("/")
def root():
    return {
        "system": "DBPTBS",
        "status": "PROTECTED",
        "docs": "/docs",
        "note": "Prototype - simulated wallets and behavioural data only. Data resets on every restart.",
    }
