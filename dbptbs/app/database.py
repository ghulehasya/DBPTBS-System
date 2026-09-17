"""
DBPTBS - Database Layer
--------------------------
Plain sqlite3 (stdlib) rather than an ORM. For a 48-hour hackathon MVP with
four simple tables and no concurrent-writer requirements, this keeps the
dependency list minimal and every query auditable at a glance. All data
here is synthetic/simulated - no real user, wallet, or financial data.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    wallet_address TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS behavioral_profiles (
    user_id TEXT PRIMARY KEY,
    dna_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    amount REAL NOT NULL,
    timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL,
    behaviour_similarity REAL NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    assessment_json TEXT
);

CREATE TABLE IF NOT EXISTS security_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    risk_score REAL,
    timestamp TEXT NOT NULL,
    description TEXT
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
def upsert_user(user_id: str, username: str, wallet_address: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, username, wallet_address, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET username=excluded.username, wallet_address=excluded.wallet_address",
            (user_id, username, wallet_address, datetime.now(timezone.utc).isoformat()),
        )


def get_user(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Behavioural profiles (Digital DNA)
# ---------------------------------------------------------------------------
def save_dna(user_id: str, dna_dict: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO behavioral_profiles (user_id, dna_json, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET dna_json=excluded.dna_json, updated_at=excluded.updated_at",
            (user_id, json.dumps(dna_dict, default=str), datetime.now(timezone.utc).isoformat()),
        )


def load_dna(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT dna_json FROM behavioral_profiles WHERE user_id = ?", (user_id,)).fetchone()
        return json.loads(row["dna_json"]) if row else None


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def record_transaction(
    sender: str, recipient: str, amount: float, risk_score: float,
    behaviour_similarity: float, status: str, reason: str, assessment: dict,
) -> str:
    tx_id = uuid.uuid4().hex[:12]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (id, sender, recipient, amount, timestamp, risk_score, "
            "behaviour_similarity, status, reason, assessment_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tx_id, sender, recipient, amount, datetime.now(timezone.utc).isoformat(),
                risk_score, behaviour_similarity, status, reason, json.dumps(assessment),
            ),
        )
    return tx_id


def update_transaction_status(tx_id: str, status: str, reason: str = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET status = ?, reason = COALESCE(?, reason) WHERE id = ?",
            (status, reason, tx_id),
        )


def get_transaction(tx_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        return dict(row) if row else None


def list_transactions(sender: Optional[str] = None, limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        if sender:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE sender = ? ORDER BY timestamp DESC LIMIT ?",
                (sender, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def count_recent_transactions(sender: str, hours: int = 24) -> int:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT timestamp FROM transactions WHERE sender = ? ORDER BY timestamp DESC LIMIT 500",
            (sender,),
        ).fetchall()
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    count = 0
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["timestamp"]).timestamp()
        except ValueError:
            continue
        if ts >= cutoff:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Security events
# ---------------------------------------------------------------------------
def log_security_event(user_id: str, event_type: str, risk_score: float, description: str) -> str:
    event_id = uuid.uuid4().hex[:12]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO security_events (event_id, user_id, event_type, risk_score, timestamp, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, user_id, event_type, risk_score, datetime.now(timezone.utc).isoformat(), description),
        )
    return event_id


def list_security_events(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
