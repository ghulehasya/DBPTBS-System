"""
DBPTBS - Orchestration Engine
-------------------------------
The single place that wires together: synthetic data -> Digital DNA ->
anomaly detector -> risk engine -> additional authentication -> blockchain
-> database. Both the FastAPI routes and the Streamlit dashboard call
*only* into this module, so there is exactly one implementation of the
actual security pipeline (no duplicated logic between "API version" and
"UI version").

In-memory session state (generator/DNA/detector/blockchain per user) is
kept in a process-wide registry. This is a single-process hackathon demo;
a production system would persist and reload trained detectors instead of
holding them in memory.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from app import database as db
from app.services.anomaly_detector import AnomalyDetector, build_and_fit_detector
from app.services.auth_challenge import demo_challenge_store
from app.services.blockchain import Blockchain
from app.services.dna_engine import DigitalDNA, adapt_baseline, build_digital_dna
from app.services.risk_engine import RiskAssessment, assess_transaction
from app.services.synthetic_data import UserBehaviourGenerator, new_demo_user

HISTORY_SIZE = 150


@dataclass
class UserSession:
    user_id: str
    generator: UserBehaviourGenerator
    dna: DigitalDNA
    detector: AnomalyDetector
    blockchain: Blockchain = field(default_factory=Blockchain)


_sessions: Dict[str, UserSession] = {}
_lock = threading.Lock()


def _bootstrap_user(user_id: str, seed: int = 7) -> UserSession:
    generator = new_demo_user(user_id=user_id, seed=seed)
    raw_history = generator.sample_history(HISTORY_SIZE)
    history = [dict(**e.to_feature_dict(), recipient=e.recipient, timestamp=e.timestamp) for e in raw_history]
    dna = build_digital_dna(user_id, history)
    detector = build_and_fit_detector(dna, history)

    db.init_db()
    db.upsert_user(user_id, username=f"demo_{user_id.lower()}", wallet_address=dna.trusted_recipients[0])
    db.save_dna(user_id, dna.to_dict())

    return UserSession(user_id=user_id, generator=generator, dna=dna, detector=detector)


def get_session(user_id: str = "USR001") -> UserSession:
    with _lock:
        if user_id not in _sessions:
            _sessions[user_id] = _bootstrap_user(user_id)
        return _sessions[user_id]


def reset_session(user_id: str = "USR001") -> UserSession:
    with _lock:
        _sessions.pop(user_id, None)
    return get_session(user_id)


# ---------------------------------------------------------------------------
# Core pipeline: User Login -> ... -> Risk Score -> Allow/Block
# ---------------------------------------------------------------------------
@dataclass
class TransactionOutcome:
    tx_id: str
    assessment: RiskAssessment
    status: str            # APPROVED / HELD_FOR_VERIFICATION / BLOCKED
    otp_code_for_demo: Optional[str] = None  # ONLY populated because this is a prototype demo


def analyze_and_decide(
    user_id: str,
    amount: float,
    recipient: str,
    when: datetime = None,
    interaction_overrides: Optional[dict] = None,
    behaviour_profile: str = "legitimate",  # "legitimate" or "attacker" - simulation control only
) -> TransactionOutcome:
    """The full pre-transaction pipeline for one transaction attempt."""
    session = get_session(user_id)
    when = when or datetime.now()

    if interaction_overrides:
        base_event = session.generator.sample_legitimate_event(when=when)
        feature_event = base_event.to_feature_dict()
        feature_event.update(interaction_overrides)
    elif behaviour_profile == "attacker":
        ev = session.generator.sample_attacker_event(subtle=False)
        feature_event = ev.to_feature_dict()
    else:
        ev = session.generator.sample_legitimate_event(when=when)
        feature_event = ev.to_feature_dict()

    feature_event["amount"] = amount
    feature_event["recipient"] = recipient
    feature_event["hour"] = when.hour

    recent_count = db.count_recent_transactions(user_id, hours=24) + 1

    anomaly = session.detector.score(feature_event)
    assessment = assess_transaction(feature_event, session.dna, anomaly, recent_tx_count_24h=recent_count)

    if assessment.decision in ("LOW", "MEDIUM"):
        status = "APPROVED"
        reason = "Behavioural profile consistent with account owner."
        block = session.blockchain.add_transaction(
            {
                "sender": user_id, "recipient": recipient, "amount": amount,
                "risk_score": assessment.risk_score, "timestamp": when.isoformat(),
            }
        )
        otp = None
        if assessment.decision == "LOW":
            adapt_baseline(session.dna, feature_event)
            db.save_dna(user_id, session.dna.to_dict())
    else:
        status = "HELD_FOR_VERIFICATION"
        reason = "Behavioural deviation strongly suggests unauthorized activity; additional verification required."
        otp = None

    tx_id = db.record_transaction(
        sender=user_id, recipient=recipient, amount=amount,
        risk_score=assessment.risk_score, behaviour_similarity=assessment.behavioural_similarity_pct,
        status=status, reason=reason, assessment=assessment.to_dict(),
    )

    if status == "HELD_FOR_VERIFICATION":
        challenge = demo_challenge_store.issue(tx_id)
        otp = challenge.code  # prototype only: shown directly, never actually transmitted anywhere

    db.log_security_event(
        user_id=user_id,
        event_type=f"TRANSACTION_{status}",
        risk_score=assessment.risk_score,
        description="; ".join(assessment.reasons) if assessment.reasons else "Nominal transaction.",
    )

    return TransactionOutcome(tx_id=tx_id, assessment=assessment, status=status, otp_code_for_demo=otp)


def verify_and_release(user_id: str, tx_id: str, code: str) -> dict:
    session = get_session(user_id)
    ok, message = demo_challenge_store.verify(tx_id, code)

    if ok:
        tx = db.get_transaction(tx_id)
        block = session.blockchain.add_transaction(
            {
                "sender": tx["sender"], "recipient": tx["recipient"], "amount": tx["amount"],
                "risk_score": tx["risk_score"], "timestamp": tx["timestamp"],
            },
            approved_by="DBPTBS+ManualVerification",
        )
        db.update_transaction_status(tx_id, "APPROVED", "Owner identity verified via step-up challenge.")
        db.log_security_event(user_id, "VERIFICATION_SUCCESS", 0, f"Transaction {tx_id} released after verification.")
        return {"verified": True, "message": message, "block_index": block.index}
    else:
        challenge = demo_challenge_store.get(tx_id)
        if challenge and challenge.attempts_used >= 3:
            db.update_transaction_status(tx_id, "BLOCKED", "Verification failed after maximum attempts.")
            db.log_security_event(user_id, "VERIFICATION_FAILED_FINAL", 0, f"Transaction {tx_id} permanently blocked.")
        return {"verified": False, "message": message, "block_index": None}


def run_scenario_legitimate(user_id: str = "USR001") -> TransactionOutcome:
    session = get_session(user_id)
    ev = session.generator.scenario_legitimate()
    return analyze_and_decide(
        user_id, amount=ev.amount, recipient=ev.recipient, when=ev.timestamp,
        interaction_overrides=ev.to_feature_dict(), behaviour_profile="legitimate",
    )


def run_scenario_attack(user_id: str = "USR001") -> TransactionOutcome:
    session = get_session(user_id)
    ev = session.generator.scenario_account_takeover()
    return analyze_and_decide(
        user_id, amount=ev.amount, recipient=ev.recipient, when=ev.timestamp,
        interaction_overrides=ev.to_feature_dict(), behaviour_profile="attacker",
    )


def get_dna_visualization(user_id: str, last_assessment: Optional[RiskAssessment] = None) -> dict:
    """Six-dimension "pattern match" view for the Digital DNA visualisation
    panel. Every percentage is 100% minus the *actual* risk-engine unit
    score for that dimension from the most recent assessment - never a
    hand-set UI value. With no assessment yet, every dimension defaults to
    100% (no deviation observed yet)."""
    dims = {"Transaction Pattern": "transaction_amount", "Time Pattern": "time",
            "Recipient Pattern": "recipient", "Session Pattern": "session",
            "Mouse Pattern": "mouse", "Typing Pattern": "typing"}
    if last_assessment is None:
        return {label: 100.0 for label in dims}
    by_name = {c.name: c for c in last_assessment.components}
    return {label: round(100.0 * (1.0 - by_name[key].unit_score), 1) for label, key in dims.items()}


def get_stats(user_id: str) -> dict:
    txs = db.list_transactions(sender=user_id, limit=500)
    approved = sum(1 for t in txs if t["status"] == "APPROVED")
    held = sum(1 for t in txs if t["status"] == "HELD_FOR_VERIFICATION")
    blocked = sum(1 for t in txs if t["status"] == "BLOCKED")
    avg_similarity = round(sum(t["behaviour_similarity"] for t in txs) / len(txs), 1) if txs else 100.0
    latest_risk = txs[0]["risk_score"] if txs else 0.0
    return {
        "protected_count": len(txs),
        "approved": approved,
        "suspicious": held,
        "blocked": blocked,
        "trust_score": avg_similarity,
        "current_risk": latest_risk,
    }
